from flask import Flask, request, Response
import logging
import xml.etree.ElementTree as ET

# Set up logging
logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

@app.route('/process_xml', methods=['POST'])
def process_xml():
    try:
        # Parse the incoming XML
        xml_data = request.data
        logging.info(f"Received XML: {xml_data}")
        
        # Parse the XML into an ElementTree object
        tree = ET.ElementTree(ET.fromstring(xml_data))
        root = tree.getroot()
        
        # Find all elements named "text" and reverse their content
        for text_element in root.findall('.//text'):
            original_text = text_element.text
            reversed_text = original_text[::-1]  # Reverse the text
            text_element.text = reversed_text
            logging.info(f"Reversed Text: {reversed_text}")
        
        # Convert the ElementTree back to XML string
        xml_response = ET.tostring(root, encoding='unicode', method='xml')
        
        # Log the processed XML response
        logging.info(f"Processed XML (reversed): {xml_response}")
        
        # Return the XML response with the reversed text
        return Response(xml_response, mimetype='application/xml')
        
    except Exception as e:
        logging.error(f"Error processing XML: {e}")
        return Response(f"<error>{str(e)}</error>", mimetype='application/xml')

if __name__ == "__main__":
    app.run(debug=True, port=5001)
