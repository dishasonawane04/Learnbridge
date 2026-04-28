from xhtml2pdf import pisa
from io import BytesIO

def test_basic_pdf():
    html = "<html><body><h1>Hello World</h1></body></html>"
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        with open('basic_test.pdf', 'wb') as f:
            f.write(result.getvalue())
        print("Basic PDF generated.")
    else:
        print("Basic PDF generation failed.")

if __name__ == "__main__":
    test_basic_pdf()
