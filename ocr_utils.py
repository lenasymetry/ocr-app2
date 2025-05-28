import requests
import tempfile
from PIL import Image

def ocr_space_file(image, api_key='K86130833088957'):
    """
    Envoie une image PIL à l'API OCR.Space après l'avoir sauvegardée
    temporairement sur disque pour éviter l'erreur AttributeError.
    """
    with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp_file:
        image.save(tmp_file.name, format='PNG')
        payload = {
            'isOverlayRequired': False,
            'apikey': api_key,
            'language': 'fre'
        }
        with open(tmp_file.name, 'rb') as f:
            files = {
                'file': ('image.png', f, 'image/png')
            }
            response = requests.post('https://api.ocr.space/parse/image',
                                     files=files,
                                     data=payload,
                                     )
    result = response.json()
    try:
        return result['ParsedResults'][0]['ParsedText']
    except (KeyError, IndexError):
        return ""
