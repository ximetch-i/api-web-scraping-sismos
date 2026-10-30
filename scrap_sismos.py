import requests
from bs4 import BeautifulSoup
import boto3
import uuid

def lambda_handler(event, context):
    # URL de la pagina del IGP con los reportes sismicos
    url = "https://ultimosismo.igp.gob.pe/productos/reportes-sismicos"

    # Realizar la solicitud HTTP a la pagina web
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': 'Error al acceder a la pagina web'
        }

    # Parsear el contenido HTML de la pagina web
    soup = BeautifulSoup(response.content, 'html.parser')

    # Encontrar la tabla en el HTML
    table = soup.find('table')
    if not table:
        return {
            'statusCode': 404,
            'body': 'No se encontro la tabla en la pagina web'
        }

    # Extraer los encabezados de la tabla
    headers = [th.get_text(strip=True) for th in table.find_all('th')]

    # Extraer las filas de la tabla (solo los 10 ultimos sismos)
    rows = []
    for tr in table.find_all('tr'):
        cells = tr.find_all('td')
        if not cells:  # Omitir la fila de encabezado
            continue
        fila = {}
        for i, cell in enumerate(cells):
            nombre = headers[i] if i < len(headers) and headers[i] else f"columna_{i+1}"
            fila[nombre] = cell.get_text(strip=True)
        rows.append(fila)
        if len(rows) == 10:
            break

    # Guardar los datos en DynamoDB
    dynamodb = boto3.resource('dynamodb')
    tabla = dynamodb.Table('TablaSismosIGP')

    # Eliminar todos los elementos de la tabla antes de agregar los nuevos
    scan = tabla.scan()
    with tabla.batch_writer() as batch:
        for each in scan['Items']:
            batch.delete_item(Key={'id': each['id']})

    # Insertar los nuevos datos
    i = 1
    for row in rows:
        row['#'] = i
        row['id'] = str(uuid.uuid4())  # ID unico para cada sismo
        tabla.put_item(Item=row)
        i = i + 1

    # Retornar el resultado como JSON
    return {
        'statusCode': 200,
        'body': rows
    }
