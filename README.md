# **PRODVI - AI-Powered Peer Review & Performance Evaluation System**

![PRODVI Badge](https://img.shields.io/badge/PRODVI-AI%20Powered-blue?style=for-the-badge)
![Django](https://img.shields.io/badge/Django-4.2.7-green?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat-square)
![Status](https://img.shields.io/badge/Status-Live-success?style=flat-square)

> **A comprehensive peer review and performance evaluation platform powered by AI and machine learning for modern workplace assessment.**

---

## 🌟 **Overview**

**PRODVI** revolutionizes workplace performance evaluation by combining traditional peer review processes with cutting-edge AI technology. The platform enables organizations to create, manage, and analyze employee performance reviews with intelligent insights powered by **Google's Gemini AI** and custom machine learning models.

---

## ✨ **Key Features**

### 🎯 **Core Functionality**
- **Dynamic Form Creation** - Admins can create custom evaluation forms with flexible questions
- **Peer Review System** - Employees can review colleagues with structured assessments
- **Role-Based Access** - Separate dashboards for admins and employees
- **Real-Time Analytics** - Interactive charts and performance visualizations

### 🤖 **AI-Powered Intelligence**
- **ML-Based Rating System** - Automatic performance scoring using scikit-learn models
- **Gemini AI Integration** - Intelligent analysis and summary generation
- **Sentiment Analysis** - Advanced text processing for review insights

### 📊 **Advanced Analytics**
- **Interactive Dashboards** - Real-time performance metrics and trends
- **Visual Charts** - Pie charts, line graphs, and progress indicators
- **Comprehensive Reports** - Detailed performance summaries for each employee
- **Growth Tracking** - Historical performance analysis and improvement insights

---

## 🚀 **Live Demo**

### **🌐 [https://prodvi.onrender.com](https://prodvi.onrender.com)**

#### **Demo Credentials:**
- **Admin Access:** Create your own account via signup
- **Employee Access:** Create your own account via signup

---

## 🛠 **Technology Stack**

### **Backend**
- **Framework:** Django 4.2.7
- **Database:** PostgreSQL (Production) / SQLite (Development)
- **Authentication:** Custom User Model with Role-Based Access
- **API Integration:** Google Gemini AI

### **Frontend**
- **Templating:** Django Templates with Modern CSS
- **Charts:** Chart.js for interactive visualizations
- **Styling:** Custom CSS with responsive design

### **AI/ML Stack**
- **Machine Learning:** scikit-learn for performance prediction
- **AI Analysis:** Google Gemini API for intelligent summaries
- **Data Processing:** Pandas, NumPy for data manipulation
- **Text Processing:** Advanced NLP NLTK algos for review analysis

### **Deployment**
- **Platform:** Render (Production)
- **Static Files:** WhiteNoise for efficient asset serving
- **Database:** PostgreSQL with automated migrations
- **CI/CD:** GitHub integration with automatic deployments

---

## 📋 **Installation & Setup**

### **Prerequisites**
- Python 3.10+
- Git
- Google Gemini API Key

### **Local Development Setup**
- 1. Clone the repository
  git clone https://github.com/MelwinDas/prodvi-django.git
  cd prodvi-django

- 2. Create virtual environment
  python -m venv prodvi_env
  source prodvi_env/bin/activate # On Windows: prodvi_env\Scripts\activate

- 3. Install dependencies
  pip install -r requirements.txt

- 4. Environment setup
  cp .env.example .env
  Edit .env with your API keys

- 5. Database setup
  python manage.py migrate

- 6. Run development server
  python manage.py runserver

### **Environment Variables**
- SECRET_KEY=your-django-secret-key
- GEMINI_API_KEY=your-gemini-api-key
- DATABASE_URL=your-database-url # For production 


## 🎮 **Usage Guide**

### **For Administrators**
1. **Login** to admin dashboard
2. **Create Evaluation Forms** with custom questions
3. **Assign Employees** to specific forms
4. **Monitor Submissions** and review progress
5. **View Analytics** and generate reports
6. **Access AI Summaries** for comprehensive insights

### **For Employees**
1. **Register/Login** to employee dashboard
2. **View Assigned Forms** for peer reviews
3. **Submit Colleague Reviews** with detailed feedback
4. **Track Your Performance** through personal analytics
5. **View AI-Generated Summaries** of your performance

## 📁 **Project Structure** 
```
prodvi-django/
├── evaluation/ # Main Django app
│ ├── models.py # Database models
│ ├── views.py # Business logic
│ ├── ml_models/ # ML model files
│ └── templates/ # HTML templates
├── prodvi_project/ # Django settings
├── requirements.txt # Dependencies
├── build.sh # Deployment script
└── README.md # This file
```

## 🚀 **Deployment**

### **Render Deployment (Recommended)**
1. **Fork** this repository
2. **Create account** on [Render](https://render.com)
3. **Create PostgreSQL** database
4. **Create web service** connected to your GitHub
5. **Set environment variables**
6. **Deploy automatically!** 

## 📄 **License**

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- **Google Gemini AI** for intelligent text analysis
- **Django Community** for the robust framework
- **Render** for free hosting platform
- **scikit-learn** for machine learning capabilities
- **Chart.js** for beautiful visualizations

---

## ⭐ **Support**

**Star this repository if you found it helpful!**


