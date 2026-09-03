import os
import json
import cv2  # type: ignore
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sample_documents")
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "uploads")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

def draw_face(img, center_x, center_y, scale=1.0, is_alternate_person=False):
    """Draws recognizable facial structure on document canvas."""
    cx, cy = int(center_x), int(center_y)
    r_w, r_h = int(55 * scale), int(75 * scale)
    
    if not is_alternate_person:
        # Person A (Primary synthetic passport holder: Arjun Kumar)
        cv2.ellipse(img, (cx, cy), (r_w, r_h), 0, 0, 360, (130, 110, 80), -1)
        eye_ox, eye_oy = int(22 * scale), int(18 * scale)
        cv2.circle(img, (cx - eye_ox, cy - eye_oy), int(9 * scale), (255, 255, 255), -1)
        cv2.circle(img, (cx + eye_ox, cy - eye_oy), int(9 * scale), (255, 255, 255), -1)
        cv2.circle(img, (cx - eye_ox, cy - eye_oy), int(4 * scale), (30, 30, 30), -1)
        cv2.circle(img, (cx + eye_ox, cy - eye_oy), int(4 * scale), (30, 30, 30), -1)
        cv2.ellipse(img, (cx, cy + int(24 * scale)), (int(22 * scale), int(10 * scale)), 0, 0, 180, (40, 40, 40), 2)
    else:
        # Person B (Alternate synthetic person: different skin tone, spectacles, mustache)
        cv2.ellipse(img, (cx, cy), (int(65 * scale), int(68 * scale)), 0, 0, 360, (45, 65, 95), -1)
        # Eyeglasses
        cv2.rectangle(img, (cx - int(45 * scale), cy - int(25 * scale)), (cx - int(10 * scale), cy - int(5 * scale)), (20, 20, 20), 2)
        cv2.rectangle(img, (cx + int(10 * scale), cy - int(25 * scale)), (cx + int(45 * scale), cy - int(5 * scale)), (20, 20, 20), 2)
        cv2.line(img, (cx - int(10 * scale), cy - int(15 * scale)), (cx + int(10 * scale), cy - int(15 * scale)), (20, 20, 20), 2)
        cv2.circle(img, (cx - int(27 * scale), cy - int(15 * scale)), int(4 * scale), (10, 10, 10), -1)
        cv2.circle(img, (cx + int(27 * scale), cy - int(15 * scale)), int(4 * scale), (10, 10, 10), -1)
        # Mustache
        cv2.rectangle(img, (cx - int(30 * scale), cy + int(18 * scale)), (cx + int(30 * scale), cy + int(28 * scale)), (15, 15, 15), -1)

def generate_passport(
    filename,
    name,
    passport_num,
    dob,
    expiry,
    issue="10/05/2020",
    is_tampered_photo=False,
    is_photo_swap=False,
    mrz_num_override=None,
    mrz_dob_override=None
):
    img = np.full((520, 800, 3), 246, dtype=np.uint8)

    # Header
    cv2.rectangle(img, (0, 0), (800, 75), (75, 45, 20), -1)
    cv2.putText(img, "PASSPORT - REPUBLIC OF INDIA", (150, 48), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)

    # Photo Box
    cv2.rectangle(img, (40, 110), (220, 340), (200, 200, 200), -1)
    cv2.rectangle(img, (40, 110), (220, 340), (100, 100, 100), 2)
    
    # Draw photo (or swapped face)
    draw_face(img, 130, 215, scale=0.95, is_alternate_person=is_photo_swap)

    if is_tampered_photo or is_photo_swap:
        # Visual splicing boundary artifact
        cv2.rectangle(img, (36, 106), (224, 344), (0, 0, 255), 3)
        cv2.putText(img, "SPLICED PHOTO EDGE", (42, 335), cv2.FONT_HERSHEY_PLAIN, 0.9, (0, 0, 255), 2)

    # Fields
    parts = name.split()
    surname = parts[-1] if len(parts) > 1 else name
    given = " ".join(parts[:-1]) if len(parts) > 1 else "HOLDER"
    
    fields = [
        ("Type / Code", "P / IND"),
        ("Passport No.", passport_num),
        ("Surname", surname),
        ("Given Name(s)", given),
        ("Nationality", "INDIAN"),
        ("Sex", "M"),
        ("Date of Birth", dob),
        ("Date of Issue", issue),
        ("Date of Expiry", expiry)
    ]

    y_offset = 108
    for label, val in fields:
        cv2.putText(img, label.upper(), (260, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 120, 120), 1)
        font_color = (0, 0, 190) if (mrz_dob_override and label == "Date of Birth") else (25, 25, 25)
        cv2.putText(img, val, (260, y_offset + 20), cv2.FONT_HERSHEY_DUPLEX, 0.62, font_color, 2)
        y_offset += 36

    # MRZ Area
    cv2.rectangle(img, (0, 420), (800, 520), (232, 232, 232), -1)
    cv2.line(img, (0, 420), (800, 420), (160, 160, 160), 2)

    try:
        from mrz.generator.td3 import TD3CodeGenerator  # type: ignore
        d_parts = dob.split("/")
        dob_yy = d_parts[2][-2:] + d_parts[1] + d_parts[0]
        e_parts = expiry.split("/")
        exp_yy = e_parts[2][-2:] + e_parts[1] + e_parts[0]

        td3 = TD3CodeGenerator(
            document_type='P',
            country_code='IND',
            surname='SINGH',
            given_names=given.upper(),
            document_number=passport_num,
            nationality='IND',
            birth_date=dob_yy,
            sex='M',
            expiry_date=exp_yy,
            optional_data=''
        )
        mrz_lines = str(td3).splitlines()
        mrz1 = mrz_lines[0]
        mrz2 = mrz_lines[1]
    except Exception:
        given_clean = "<".join(given.split()).upper()
        mrz1 = f"P<INDSINGH<<{given_clean}".ljust(44, "<")
        mrz2 = f"{passport_num}<6IND9608144M3005095<<<<<<<<<<<<<<06"

    # Apply intentional tampering overrides for tampered/text-altered test scenarios
    if mrz_num_override:
        mrz2 = f"{mrz_num_override}<4IND9608144M3005094<<<<<<<<<<<<<<<04"
    if mrz_dob_override:
        mrz2 = mrz2[:13] + mrz_dob_override + mrz2[13+len(mrz_dob_override):]

    # Synthetic Demonstration Watermark
    cv2.putText(img, "SYNTHETIC DEMONSTRATION DATA - NOT AN OFFICIAL ID", (250, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 140, 140), 1)

    cv2.putText(img, mrz1, (25, 458), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (10, 10, 10), 2)
    cv2.putText(img, mrz2, (25, 498), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (10, 10, 10), 2)




    out_path = os.path.join(DATA_DIR, filename)
    cv2.imwrite(out_path, img)
    
    meta_path = out_path + ".meta.json"
    with open(meta_path, "w") as f:
        json.dump({
            "document_type": "PASSPORT",
            "name": f"{given} {surname}",
            "surname": surname,
            "passport_number": passport_num,
            "nationality": "INDIAN",
            "dob": dob,
            "issue_date": issue,
            "expiry_date": expiry,
            "gender": "M",
            "mrz_line1": mrz1,
            "mrz_line2": mrz2
        }, f, indent=2)
    print(f"Created: {out_path}")

def generate_aadhaar(filename, name, aadhaar_num, dob, gender="MALE", is_tampered=False):
    img = np.full((480, 750, 3), 250, dtype=np.uint8)

    # Tricolor Strip
    cv2.rectangle(img, (0, 0), (750, 20), (30, 120, 255), -1)  # Saffron
    cv2.rectangle(img, (0, 20), (750, 40), (255, 255, 255), -1) # White
    cv2.rectangle(img, (0, 40), (750, 60), (30, 150, 20), -1)   # Green

    cv2.putText(img, "GOVERNMENT OF INDIA - UNIQUE IDENTIFICATION AUTHORITY", (70, 90),
                cv2.FONT_HERSHEY_DUPLEX, 0.55, (20, 20, 20), 1)

    # Photo Box
    cv2.rectangle(img, (40, 120), (200, 320), (210, 210, 210), -1)
    cv2.rectangle(img, (40, 120), (200, 320), (100, 100, 100), 2)
    draw_face(img, 120, 210, scale=0.85, is_alternate_person=False)

    # Fields
    cv2.putText(img, name, (240, 160), cv2.FONT_HERSHEY_DUPLEX, 0.8, (10, 10, 10), 2)
    cv2.putText(img, f"DOB: {dob}", (240, 205), cv2.FONT_HERSHEY_DUPLEX, 0.65, (30, 30, 30), 2)
    cv2.putText(img, f"Gender: {gender}", (240, 245), cv2.FONT_HERSHEY_DUPLEX, 0.65, (30, 30, 30), 2)

    # Aadhaar Number
    cv2.rectangle(img, (0, 380), (750, 470), (235, 240, 245), -1)
    font_color = (0, 0, 200) if is_tampered else (10, 10, 10)
    cv2.putText(img, aadhaar_num, (180, 435), cv2.FONT_HERSHEY_DUPLEX, 1.1, font_color, 2)
    cv2.putText(img, "SYNTHETIC DEMONSTRATION DATA - NOT AN OFFICIAL ID", (170, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 140, 140), 1)

    out_path = os.path.join(DATA_DIR, filename)

    cv2.imwrite(out_path, img)

    meta_path = out_path + ".meta.json"
    with open(meta_path, "w") as f:
        json.dump({
            "document_type": "AADHAAR",
            "name": name,
            "aadhaar_number": aadhaar_num.replace(" ", ""),
            "dob": dob,
            "gender": gender,
            "address": "New Delhi, India"
        }, f, indent=2)
    print(f"Created: {out_path}")

def generate_traveler_portrait(filename, is_alternate=False):
    """Generates standalone live photo of traveler."""
    img = np.full((400, 400, 3), 235, dtype=np.uint8)
    cv2.rectangle(img, (0, 0), (400, 400), (220, 225, 230), -1)
    draw_face(img, 200, 200, scale=1.3, is_alternate_person=is_alternate)
    
    out_path = os.path.join(DATA_DIR, filename)
    cv2.imwrite(out_path, img)
    print(f"Created: {out_path}")

if __name__ == "__main__":
    # 1. Genuine Passport (Arjun Kumar, valid MRZ, clean)
    generate_passport(
        "sample_passport_genuine.jpg",
        "ARJUN KUMAR SINGH",
        "K1234567",
        "14/08/1996",
        "09/05/2030",
        is_tampered_photo=False
    )

    # 2. Tampered Passport (Photo swap edge artifact + MRZ checksum mismatch)
    generate_passport(
        "sample_passport_tampered.jpg",
        "VIKRAM CHOUDHARY",
        "K9876543",
        "01/01/1985",
        "09/05/2025",
        is_tampered_photo=True,
        mrz_num_override="K9999999"
    )

    # 3. Photo-Swapped Passport
    generate_passport(
        "sample_passport_photoswap.jpg",
        "ARJUN KUMAR SINGH",
        "K1234567",
        "14/08/1996",
        "09/05/2030",
        is_tampered_photo=True,
        is_photo_swap=True
    )

    # 4. Text-Altered Passport (Printed DOB 14/08/1996 vs MRZ DOB 850512)
    generate_passport(
        "sample_passport_textaltered.jpg",
        "ARJUN KUMAR SINGH",
        "K1234567",
        "14/08/1996",
        "09/05/2030",
        is_tampered_photo=False,
        mrz_dob_override="850512"
    )

    # 5. Blacklisted Passport (Matches database entry Z9982341)
    generate_passport(
        "sample_passport_blacklisted.jpg",
        "RAJESH KUMAR",
        "Z9982341",
        "15/04/1988",
        "14/04/2028",
        is_tampered_photo=False,
        is_photo_swap=True
    )



    # 6. Genuine Aadhaar (Valid Verhoeff checksum)
    generate_aadhaar(
        "sample_aadhaar_genuine.jpg",
        "RAJESH SHARMA",
        "2345 6789 0128",
        "12/03/1992",
        gender="MALE",
        is_tampered=False
    )

    # 7. Tampered Aadhaar (Invalid Verhoeff checksum)
    generate_aadhaar(
        "sample_aadhaar_tampered.jpg",
        "ANIL VERMA",
        "1234 5678 9012",
        "01/01/1850",
        gender="MALE",
        is_tampered=True
    )

    # Traveler portraits
    generate_traveler_portrait("sample_traveler_match.jpg", is_alternate=False)
    generate_traveler_portrait("sample_traveler_mismatch.jpg", is_alternate=True)

    # Sync to uploads folder for static serving
    for fname in os.listdir(DATA_DIR):
        src = os.path.join(DATA_DIR, fname)
        dst = os.path.join(UPLOADS_DIR, fname)
        if os.path.isfile(src):
            with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                fdst.write(fsrc.read())

    print("All synthetic calibration samples successfully created and synchronized.")
