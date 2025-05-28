import streamlit as st
import os
import tempfile
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import numpy as np
import cv2
import re

# Chemin vers tesseract sur ta machine locale (à adapter ou commenter si sur Streamlit Cloud)
# pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

st.set_page_config(layout="wide")

# Affichage logo si tu as
logo_path = "mon_logo.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=320)

st.title("🔎 OCR Documents Administratifs")

# Sidebar
st.sidebar.header("Types de documents à retrouver")
ci_check = st.sidebar.checkbox("Carte d'identité", True)
passeport_check = st.sidebar.checkbox("Passeport", True)
ts_check = st.sidebar.checkbox("Titre de séjour", True)
jd_check = st.sidebar.checkbox("Justificatif de domicile", False)
rib_check = st.sidebar.checkbox("RIB", False)

st.sidebar.header("Filtrer par nom/prénom (obligatoire)")
nom_cible = st.sidebar.text_input("Nom")
prenom_cible = st.sidebar.text_input("Prénom")

# Fonctions d'amélioration d'image
def needs_enhancement(img_cv):
    gray = img_cv if len(img_cv.shape) == 2 else cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    fm = cv2.Laplacian(gray, cv2.CV_64F).var()
    return fm < 100

def prepare_ocr_image(pil_image):
    img_cv = np.array(pil_image)
    if len(img_cv.shape) == 3:
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    if needs_enhancement(img_cv):
        img_cv = cv2.medianBlur(img_cv, 3)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        img_cv = clahe.apply(img_cv)
        img_cv = cv2.adaptiveThreshold(img_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
    return Image.fromarray(img_cv)

def extraire_texte_image(image):
    config = '--oem 3 --psm 6 -l fra+eng'
    return pytesseract.image_to_string(image, config=config)

# Détection documents selon règles spécifiques
def detect_carte_id(texte):
    mots = ["carte", "identité", "card", "identity", "republique", "république", "francaise", "française"]
    texte_min = texte.lower()
    count = sum(1 for mot in mots if mot in texte_min)
    return count >= 2

def detect_passeport(texte):
    texte_min = texte.lower()
    # Passeport seul sans "titre" ou "séjour"
    if "passeport" in texte_min and not ("titre" in texte_min or "séjour" in texte_min or "sejour" in texte_min):
        return True
    return False

def detect_titre_sejour(texte):
    mots = ["résidence", "permit", "titre", "sejour", "séjour"]
    texte_min = texte.lower()
    count = sum(1 for mot in mots if mot in texte_min)
    # S’assure d’avoir au moins 2 mots et ignore si c’est un passeport seul
    return count >= 2

def detect_justif_domicile(texte):
    mots = [
        "justificatif de domicile",
        "adresse",
        "nom du titulaire",
        "domicile",
        "quittance de loyer",
        "facture",
        "facture d'électricité", "facture edf", "facture engie", "facture gdf",
        "facture d'eau", "suez", "veolia",
        "facture de gaz",
        "attestation d'hébergement",
        "assurance habitation",
        "bail",
        "contrat de location",
        "date d’émission", "date d'emission",
        "avis d'echeance", "avis d'échéance",
        "agence",
        "montants"
    ]
    texte_min = texte.lower()
    count = sum(1 for mot in mots if mot in texte_min)
    return count >= 2

def detect_rib(texte):
    mots = [
        "relevé d'identité bancaire", "rib",
        "iban",
        "bic",
        "code banque",
        "code guichet",
        "numéro de compte", "numero de compte",
        "clé rib", "cle rib",
        "titulaire du compte",
        "nom de la banque"
    ]
    texte_min = texte.lower()
    count = sum(1 for mot in mots if mot in texte_min)
    return count >= 2

def detect_type_doc(texte):
    # Passeport prioritaire s'il seul, sinon carte identité, titre séjour...
    if passeport_check and detect_passeport(texte):
        return "Passeport"
    if ci_check and detect_carte_id(texte):
        return "Carte d'identité"
    if ts_check and detect_titre_sejour(texte):
        return "Titre de séjour"
    if jd_check and detect_justif_domicile(texte):
        return "Justificatif de domicile"
    if rib_check and detect_rib(texte):
        return "RIB"
    return None

def normalize_str(s):
    import unicodedata
    s = s.strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[^a-z\- ]", "", s)
    return s

def match_nom_prenom(texte, nom, prenom):
    if not nom and not prenom:
        return False  # Filtre obligatoire
    texte_norm = normalize_str(texte)
    nom_ok = True
    prenom_ok = True
    if nom:
        nom = normalize_str(nom)
        nom_ok = nom in texte_norm
    if prenom:
        prenom = normalize_str(prenom)
        prenom_ok = prenom in texte_norm
    return nom_ok and prenom_ok

def emoji_doc(type_doc):
    return {
        "Carte d'identité": "🪪",
        "Passeport": "🛂",
        "Titre de séjour": "🏷️",
        "Justificatif de domicile": "🏠",
        "RIB": "🏦"
    }.get(type_doc, "📄")

uploaded_files = st.file_uploader(
    "Sélectionnez vos documents (PDF ou images scannées, tout type administratif)",
    type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
    accept_multiple_files=True
)

if uploaded_files:
    resultat_affiche = False
    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        images = []
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
            images.append(Image.open(tmp_path))
        elif ext == '.pdf':
            doc = fitz.open(tmp_path)
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)

        for idx, img in enumerate(images):
            prep_img = prepare_ocr_image(img)
            texte = extraire_texte_image(prep_img)

            type_trouve = detect_type_doc(texte)
            if type_trouve and match_nom_prenom(texte, nom_cible, prenom_cible):
                resultat_affiche = True
                cible_nom = nom_cible.upper() if nom_cible else ""
                cible_prenom = prenom_cible.capitalize() if prenom_cible else ""
                st.markdown("---")
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(img, caption=f"{uploaded_file.name} / page {idx + 1}", use_container_width=True)
                with col2:
                    doc_emoji = emoji_doc(type_trouve)
                    st.markdown(
                        f"<div style='font-size:1.3em'><b>{doc_emoji} {type_trouve} détecté pour :</b></div>"
                        f"<div style='font-size:1.1em; margin-top:0.3em;'>"
                        f"<span style='color:#0078D7; font-weight:bold;'>{cible_prenom} {cible_nom}</span></div>",
                        unsafe_allow_html=True)
                    st.text_area("Texte extrait (brut)", texte, height=250)

    if not resultat_affiche:
        st.warning("Aucun document correspondant au(x) filtre(s) trouvé.")
else:
    st.info("Importez au moins un fichier PDF ou image scannée.")




