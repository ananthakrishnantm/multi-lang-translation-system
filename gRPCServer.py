import grpc
from concurrent import futures
import translation_pb2
import translation_pb2_grpc
from googletrans import Translator
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

class TranslationServiceServicer(translation_pb2_grpc.TranslationServiceServicer):
    def __init__(self):
        self.translator = Translator()
    
    def TranslateFrenchToEnglish(self, request, context):
        logging.debug(f"Received request to translate: {request.french_text}")
        
        if not request.french_text:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Empty text provided")
            return translation_pb2.TranslateResponse(english_text="")
            
        try:
            # Perform translation
            translation = self.translator.translate(
                text=request.french_text,
                src='fr',
                dest='en'
            )
            
            if not translation or not translation.text:
                raise ValueError("Translation failed - no result returned")
                
            translated_text = translation.text
            logging.debug(f"Translated text: {translated_text}")
            
            return translation_pb2.TranslateResponse(english_text=translated_text)
            
        except Exception as e:
            logging.error(f"Error during translation: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Translation failed: {str(e)}")
            return translation_pb2.TranslateResponse(english_text="")

def serve():
    # Create the gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Add the TranslationService to the server
    translation_pb2_grpc.add_TranslationServiceServicer_to_server(
        TranslationServiceServicer(), 
        server
    )
    
    # Listen on port 5002
    server.add_insecure_port('[::]:5002')
    logging.info("gRPC server starting on port 5002")
    
    # Start the server
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()