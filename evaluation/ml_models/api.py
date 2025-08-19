import os
import time
import google.generativeai as genai
from django.conf import settings

class FileProcessor:
    def __init__(self, model_name="gemini-1.5-flash"):
        # Check if API key exists in environment or Django settings
        api_key = os.environ.get("API_KEY") or getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError("API_KEY not found in environment variables or Django settings")
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 1,
                "top_p": 0.75,
                "top_k": 40,
                "max_output_tokens": 8500,
                "response_mime_type": "text/plain",
            }
        )
        
        # Get the correct paths to data files
        self.data_path = os.path.join(settings.BASE_DIR, 'evaluation', 'data')
        
        # Initialize with empty files list
        self.files = []
        self.chat_session = None
    
    def initialize_chat(self):
        """Initialize chat session with default files"""
        try:
            # Initial file paths
            initial_files = [
                os.path.join(self.data_path, "larson.txt"),
                os.path.join(self.data_path, "priya.txt")
            ]
            
            # Upload initial files
            for file_path in initial_files:
                if os.path.exists(file_path):
                    self.files.append(self.upload_to_gemini(file_path, mime_type="text/plain"))
            
            # Wait for files to be ready
            self.wait_for_files_active(self.files)
            
            # Start the chat session
            if self.files:
                self.chat_session = self.model.start_chat(
                    history=[
                        {
                            "role": "user",
                            "parts": [
                                self.files[0],
                                "Analyze the txt files containing questions and comments given by employees to one of their colleagues. Read it and give feedback about them, including areas to improve, how they can improve, and their strong points.",
                            ],
                        },
                        {
                            "role": "model",
                            "parts": [
                                "I'll analyze the employee feedback files and provide insights on areas to improve, suggestions for improvement, and strong points. Please provide the files for analysis.",
                            ],
                        }
                    ]
                )
        except Exception as e:
            print(f"Error initializing chat: {e}")
    
    def upload_to_gemini(self, path, mime_type=None):
        """Uploads the given file to Gemini and returns the file reference."""
        file = genai.upload_file(path, mime_type=mime_type)
        print(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file
    
    def wait_for_files_active(self, files):
        """Waits for the given files to be active."""
        print("Waiting for file processing...")
        for name in (file.name for file in files):
            file = genai.get_file(name)
            while file.state.name == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(10)
                file = genai.get_file(name)
            if file.state.name != "ACTIVE":
                raise Exception(f"File {file.name} failed to process")
        print("...all files ready")
    
    def process_new_file(self, file_path):
        """Uploads a new file, appends it to the list, and returns the response text."""
        if not self.chat_session:
            self.initialize_chat()
        
        # Upload new file and add it to the files list
        new_file = self.upload_to_gemini(file_path, mime_type="text/plain")
        self.files.append(new_file)
        
        # Send a message using the newly added file
        response = self.chat_session.send_message({
            "role": "user",
            "parts": [new_file]
        })
        return response.text

# Remove the example usage code that runs during import
