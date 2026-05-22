import fitz
import os

pdf_path = 'Code run.pdf'
output_dir = '.tmp/code_run_pdf_pages'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

doc = fitz.open(pdf_path)
for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    pix = page.get_pixmap()
    output_filename = f'page_{page_num:02d}.png'
    output_path = os.path.join(output_dir, output_filename)
    pix.save(output_path)
    print(f'Saved: {output_filename}')

doc.close()
