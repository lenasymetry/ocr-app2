import requests

def ocr_space_file(file, api_key='K86130833088957', language='fre'):
    payload = {
        'isOverlayRequired': True,
        'apikey': api_key,
        'language': language,
    }
    files = {
        'file': (file.name, file, 'application/octet-stream'),
    }
    response = requests.post('https://api.ocr.space/parse/image',
                             data=payload,
                             files=files)
    result = response.json()
    if result['IsErroredOnProcessing']:
        raise Exception(result['ErrorMessage'][0])
    return result['ParsedResults'][0]['ParsedText']