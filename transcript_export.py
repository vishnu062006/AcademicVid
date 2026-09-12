from fpdf import FPDF

def export_transcript_pdf(chapter, out_path: str) -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 10, chapter.chapter_title)
    pdf.ln(4)

    for section in chapter.sections:
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 8, section.title)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, f"Concept: {section.concept}")
        pdf.ln(1)
        pdf.multi_cell(0, 6, f"Real-life example: {section.indian_example}")
        pdf.ln(1)
        pdf.multi_cell(0, 6, "Key points:")
        for point in section.key_points:
            pdf.multi_cell(0, 6, f"  - {point}")
        pdf.ln(1)
        pdf.multi_cell(0, 6, f"Watch out: {section.misconception}")
        pdf.ln(6)

    pdf.output(out_path)
    return out_path