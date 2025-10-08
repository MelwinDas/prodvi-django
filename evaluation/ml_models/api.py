import os
import json
import google.generativeai as genai
from django.conf import settings

class FileProcessor:
    def __init__(self, model_name="gemini-2.5-flash"):
        # Get API key from environment or Django settings
        api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables or Django settings")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def process_new_file(self, file_path):
        """Process file content with Gemini API without file upload"""
        try:
            # Read file content directly
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Parse JSON if it's a JSON file
            if file_path.endswith('.json'):
                data = json.loads(file_content)
                formatted_content = self._format_peer_review_data(data)
            else:
                formatted_content = file_content
            
            # Create comprehensive analysis prompt
            prompt = f"""
You are an expert HR analyst. Analyze this employee peer review data and provide a comprehensive performance summary.

PEER REVIEW DATA:
{formatted_content}
(Do NOT include a date field in your output.) 
Please structure bullet points as proper Markdown lists (e.g., - for bullets, 1. 2. for numbered lists) when you generate feedback. Do NOT use extra blank lines.
Please provide a detailed analysis including:

*PERFORMANCE SUMMARY:*
- Overall performance rating (Excellent/Good/Satisfactory/Needs Improvement)
- Key performance indicators from peer feedback

*KEY STRENGTHS:*
- Top 3-5 strengths identified by colleagues
- Specific examples from peer feedback

*AREAS FOR IMPROVEMENT:*
- 2-3 main areas that need development
- Constructive suggestions for growth

*SPECIFIC RECOMMENDATIONS:*
- Actionable steps for professional development
- Skills to focus on improving
- Training or mentoring suggestions

*PEER FEEDBACK HIGHLIGHTS:*
- Most positive comments from colleagues
- Common themes in feedback

Format the response professionally as if it's going into an official performance review document. 
One Example is this:
(Employees name), your colleagues recognize your strong work ethic, commitment, and ability to produce high-quality work, often going above and beyond. You are appreciated for being supportive, bringing a positive vibe to the team, and generally being open to collaboration and feedback. Your initiative and reliability in meeting deadlines are definite strengths.
However, there are a few areas where you can focus on consistent improvement to enhance your overall effectiveness and team integration:
Communication & Collaboration: While you communicate well and are open to collaboration, there are instances where clarity in articulating your thoughts can be challenging, and a tendency to be stubborn or dismissive of others' suggestions can hinder full team synergy.
How to improve: Actively practice clarifying your thoughts before speaking. Make a conscious effort to solicit and genuinely consider diverse perspectives, even if they differ from your initial ideas. Engage more proactively in team discussions and ensure your contributions align with collective goals.
Consistency in Punctuality & Follow-Through: There's mixed feedback regarding your punctuality and consistency in task completion. While you are often on time and meet deadlines, some reports suggest frequent lateness that disrupts the team, missing start times, and occasional failure to follow through on tasks or needing reminders.
How to improve: Prioritize consistent punctuality and commitment to all tasks. Utilize time management techniques and communicate proactively and early if any delays or issues arise. This will build stronger trust and reinforce your reliability.
Stress Management: Feedback indicates that you can be challenging to work with when under stress, which affects team dynamics.
How to improve: Develop and implement strategies for managing stress effectively. This could involve better planning, time blocking, or employing stress-reduction techniques to maintain positive and productive interactions with your team, especially during high-pressure periods.
By focusing on enhancing consistent communication, ensuring reliable punctuality and follow-through, and developing robust stress management techniques, you will undoubtedly become an even more dependable and seamlessly integrated member of the team.
            
speak like a human by taking names of the employee you are evaluating you can also mention comments but never reveal which employee comented that keep everyones name confidential.
            """
            
            # Generate response
            response = self.model.generate_content(prompt)
            return response.text
            
        except FileNotFoundError:
            return f"Error: File not found at path {file_path}"
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON format in file - {str(e)}"
        except Exception as e:
            return f"Error processing with Gemini API: {str(e)}"
    
    def _format_peer_review_data(self, data):
        """Format JSON peer review data for better analysis"""
        if not isinstance(data, dict):
            return str(data)
        
        formatted = f"EMPLOYEE: {data.get('name', 'Unknown')}\n\n"
        
        questions = data.get('questions', [])
        for i, question_data in enumerate(questions, 1):
            question_text = question_data.get('question', f'Question {i}')
            answers = question_data.get('answers', [])
            
            formatted += f"QUESTION {i}: {question_text}\n"
            formatted += "PEER RESPONSES:\n"
            
            for answer in answers:
                formatted += f"- {answer}\n"
            formatted += "\n"
        
        return formatted

# For backward compatibility
def process_file(file_path):
    """Legacy function for backward compatibility"""
    processor = FileProcessor()
    return processor.process_new_file(file_path)
