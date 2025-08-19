import os
import time
import google.generativeai as genai

class FileProcessor:
    def __init__(self, model_name="gemini-1.5-flash"):
        genai.configure(api_key=os.environ["API_KEY"])
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
        
        # Initial file paths (only two files to start)
        self.files = [
            self.upload_to_gemini("clean_slate/data/larson.txt", mime_type="text/plain"),
            self.upload_to_gemini("clean_slate/data/priya.txt", mime_type="text/plain")
        ]
        
        # Wait for files to be ready for processing
        self.wait_for_files_active(self.files)
        
        # Start the chat session
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
                        "Larson, you're a valuable team member with a strong work ethic and collaborative spirit. You're reliable, always meeting deadlines, and adaptable, readily accepting feedback.  \n\nHere are a few areas for improvement:\n\n* **Communication:** Refine your communication skills by actively listening and clarifying points of confusion. Use concise and clear language in writing to prevent misunderstandings.\n* **Time Management:** Hone your time management skills by using tools, prioritizing tasks, and setting realistic deadlines. \n* **Problem Solving:** Proactively identify challenges, explore various solutions, and seek feedback on your approaches. \n\nBy focusing on these areas, you'll continue to grow and excel in your role.",
                    ],
                },
                {
                    "role": "user",
                    "parts": [
                        self.files[1],
                    ],
                },
                {
                    "role": "model",
                    "parts": [
                        "Priya, you bring a positive and supportive energy to the team, which is appreciated by everyone. You're a reliable teammate, consistently meeting deadlines and producing solid work. Your dedication and willingness to help make you a valuable asset.\n\nHere are some areas for improvement that can further enhance your contributions:\n\n* **Communication:**  While you communicate clearly in most situations, refining your ability to articulate complex ideas will help prevent misunderstandings and foster smoother collaboration. \n* **Team Collaboration:**  Engage more actively in team discussions, seek input from others, and be open to incorporating their ideas. This will strengthen team cohesion and improve project outcomes.\n* **Time Management:**  Improving your time management skills will help you meet deadlines more comfortably and contribute even more effectively to the team's goals. \n\nBy focusing on these areas, you can continue to grow and develop your skills, becoming an even more impactful member of the team.",
                    ],
                },
                {
                    "role": "user",
                    "parts": [
                        "You'll get more such file inputs; please analyze them similarly as they come.\n",
                    ],
                },
                {
                    "role": "model",
                    "parts": [
                        "Okay, I'm ready! Please provide the next file. I'll analyze it and give you feedback similar to the previous examples. \n\nJust paste the content of the file here, and I'll do my best to provide helpful insights.",
                    ],
                },
            ]
        )

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
        print()

    def process_new_file(self, file_path):
        """Uploads a new file, appends it to the list, and returns the response text."""
        # Upload new file and add it to the files list
        new_file = self.upload_to_gemini(file_path, mime_type="text/plain")
        self.files.append(new_file)

        # Send a message using the newly added file
        response = self.chat_session.send_message({
            "role": "user",
            "parts": [new_file]
        })
        return response.text 

if __name__ == "__main__":
    # Created instance of FileProcessor
    processor = FileProcessor()

    # Define the file path for the new file 
    file_path = "clean_slate/data/jordan.json"

    response_text = processor.process_new_file(file_path)
    print("Response from model:\n", response_text)
