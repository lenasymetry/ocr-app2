import streamlit as st
import os
import tempfile
import fitz  # PyMuPDF
from PIL import Image
from ocr_utils import ocr_space_file
import numpy as np
import cv2
import time

st.set_page_config(layout="wide")

# --- Affichage du logo en haut de page ---
logo_path = "mon_logo.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=320)

st.title("🔎 OCR Documents Administratifs ")

# --- SIDEBAR ---
st.sidebar.header("Types de documents à retrouver")
ci_check = st.sidebar.checkbox("Carte d'identité", True)
passeport_check = st.sidebar.checkbox("Passeport", True)
ts_check = st.sidebar.checkbox("Titre de séjour", True)
jd_check = st.sidebar.checkbox("Justificatif de domicile", False)
rib_check = st.sidebar.checkbox("RIB", False)

st.sidebar.header("Filtrer par nom/prénom (obligatoire)")
nom_cible = st.sidebar.text_input("Nom")
prenom_cible = st.sidebar.text_input("Prénom")

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

# Tu dois définir ici ou importer les fonctions suivantes :
# detect_type_doc, match_nom_prenom, emoji_doc

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
            texte = ocr_space_file(prep_img)  # Appel à l’API OCR.Space avec ta clé intégrée
            time.sleep(1.2)  # Évite de spammer l'API si plusieurs fichiers/pages

            type_trouve = detect_type_doc(texte)
            if type_trouve and match_nom_prenom(texte, nom_cible, prenom_cible):
                resultat_affiche = True
                cible_affiche_nom = nom_cible.upper() if nom_cible else ""
                cible_affiche_prenom = prenom_cible.capitalize() if prenom_cible else ""
                st.markdown("---")
                col1, col2 = st.columns([1,2])
                with col1:
                    st.image(img, caption=f"{uploaded_file.name} / page {idx + 1}", use_container_width=True)
                with col2:
                    doc_emoji = emoji_doc(type_trouve)
                    st.markdown(
                        f"<div style='font-size:1.3em'><b>{doc_emoji} {type_trouve}</b></div>"
                        f"{cible_affiche_nom}<br>{cible_affiche_prenom}",
                        unsafe_allow_html=True,
                    )
                    with st.expander("Voir le texte OCR brut"):
                        st.text_area("Texte OCR brut", value=texte, height=250, key=f"ocr_{uploaded_file.name}_{idx + 1}")
        os.unlink(tmp_path)

    if not resultat_affiche and (nom_cible or prenom_cible):
        st.info("Aucun document trouvé au nom/prénom spécifié.")
    elif not (nom_cible or prenom_cible):
        st.warning("Veuillez renseigner un nom et/ou un prénom pour activer la recherche.")


