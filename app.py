import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import tempfile
import os

# Fonctions de détection selon tes règles

def detect_carte_id(texte_min):
    mots = ["carte", "identité", "card", "identity", "republique", "république", "francaise", "française"]
    count = sum(1 for mot in mots if mot in texte_min)
    return count >= 2

def detect_passeport(texte_min):
    if "passeport" in texte_min:
        # Si titre séjour détecté, ne pas retourner passeport
        if ("titre" not in texte_min) and ("séjour" not in texte_min) and ("sejour" not in texte_min):
            return True
    return False

def detect_titre_sejour(texte_min):
    mots = ["résidence", "permit", "residence", "titre", "sejour", "séjour"]
    count = sum(1 for mot in mots if mot in texte_min)
    return count >= 2

def detect_type_doc(texte):
    texte_min = texte.lower()
    if detect_passeport(texte_min):
        return "Passeport"
    if detect_carte_id(texte_min):
        return "Carte d'identité"
    if detect_titre_sejour(texte_min):
        return "Titre de séjour"
    return "Inconnu"

# Extraction OCR PDF

def extract_text_from_pdf(pdf_path, max_pages=5):
    doc = fitz.open(pdf_path)
    textes = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        texte_page = pytesseract.image_to_string(img, lang='fra')
        textes.append(texte_page)
    doc.close()
    return textes

# Extraction OCR image

def extract_text_from_image(image_path):
    img = Image.open(image_path)
    texte = pytesseract.image_to_string(img, lang='fra')
    return [texte]

# Fonction de traitement principale

def process_document(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        textes = extract_text_from_pdf(file_path)
    elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
        textes = extract_text_from_image(file_path)
    else:
        return "Format non supporté"
    
    for texte in textes:
        doc_type = detect_type_doc(texte)
        if doc_type != "Inconnu":
            return doc_type
    return "Inconnu"

# Interface Streamlit

st.title("Détecteur de type de document")

uploaded_file = st.file_uploader("Importez un fichier PDF ou image", type=["pdf", "jpg", "jpeg", "png", "bmp", "tiff"])

if uploaded_file is not None:
    # Sauvegarde temporaire du fichier uploadé
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_filepath = tmp_file.name
    
    with st.spinner("Analyse en cours..."):
        resultat = process_document(tmp_filepath)
    
    st.success(f"Type de document détecté : **{resultat}**")
    
    # Suppression du fichier temporaire
    os.remove(tmp_filepath)



