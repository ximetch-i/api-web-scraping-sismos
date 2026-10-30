import requests
import boto3
import uuid
import json
from decimal import Decimal
from datetime import datetime

def lambda_handler(event, context):
    # Endpoint JSON que usa la pagina del IGP (se encontro en F12 > Network)
    anio = datetime.now().year
    url = f"https://ultimosismo.igp.gob.pe/api/ultimo-sismo/ajaxb/{anio}"

    # Realizar la solicitud HTTP al IGP
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': 'Error al acceder al IGP'
        }

    datos = response.json()
    if not isinstance(datos, list) or len(datos) == 0:
        return {
            'statusCode': 404,
            'body': 'No se encontraron sismos en la respuesta del IGP'
        }

    # El IGP entrega los sismos del mas antiguo al mas reciente:
    # se ordenan de mas reciente a mas antiguo y se toman los 10 ultimos
    datos.sort(key=lambda s: s['idlistasismos'], reverse=True)
    ultimos = datos[:10]

    # Quedarse con los campos utiles y dar formato a fecha y hora
    sismos = []
    for i, s in enumerate(ultimos, start=1):
        sismos.append({
            '#': i,
            'codigo': s['codigo'],
            'fecha_local': s['fecha_local'][:10],
            'hora_local': s['hora_local'][11:19],
            'fecha_utc': s['fecha_utc'][:10],
            'hora_utc': s['hora_utc'][11:19],
            'referencia': s['referencia'],
            'magnitud': s['magnitud'],
            'profundidad': s['profundidad'],
            'latitud': s['latitud'],
            'longitud': s['longitud'],
            'intensidad': s['intensidad'],
            'reporte_pdf': s['reporte_acelerometrico_pdf']
        })

    # Guardar los datos en DynamoDB
    dynamodb = boto3.resource('dynamodb')
    tabla = dynamodb.Table('TablaSismosIGP')

    # Eliminar todos los elementos de la tabla antes de agregar los nuevos
    scan = tabla.scan()
    with tabla.batch_writer() as batch:
        for each in scan['Items']:
            batch.delete_item(Key={'id': each['id']})

    # Insertar los nuevos datos
    for sismo in sismos:
        sismo['id'] = str(uuid.uuid4())  # ID unico para cada sismo
        tabla.put_item(Item=sismo)

    # Retornar el resultado como JSON
    return {
        'statusCode': 200,
        'body': sismos
    }
