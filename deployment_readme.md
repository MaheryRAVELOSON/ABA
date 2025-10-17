# ABA Framework Generator - Deployment Instructions

## 📁 Project Structure

Your project should have the following structure:

```
aba-generator/
│
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── templates/
│   └── index.html           # Web interface
└── README.md                # This file
```

## 🚀 Deploying to Render.com

### Step 1: Prepare Your Repository

1. Create a new GitHub repository
2. Create the project structure above
3. Copy all the provided files to your repository
4. Commit and push to GitHub:

```bash
git init
git add .
git commit -m "Initial commit - ABA Framework Generator"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### Step 2: Deploy on Render

1. **Go to [Render.com](https://render.com)** and sign in (or create an account)

2. **Click "New +"** → **"Web Service"**

3. **Connect your GitHub repository:**
   - Click "Connect account" if you haven't already
   - Select your ABA generator repository

4. **Configure the Web Service:**
   - **Name:** `aba-framework-generator` (or any name you prefer)
   - **Region:** Choose the closest to you
   - **Branch:** `main`
   - **Root Directory:** Leave empty
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

5. **Select the Free Plan** (or paid if you prefer)

6. **Click "Create Web Service"**

7. **Wait for deployment** (usually 2-5 minutes)
   - You'll see the build logs in real-time
   - Once complete, you'll get a URL like: `https://aba-framework-generator.onrender.com`

### Step 3: Test Your Application

1. Open the provided Render URL
2. You should see the ABA Framework Generator interface
3. Test with the default example or create your own

## 📖 Usage Instructions

### Input Format

The application accepts ABA frameworks in the following text format:

```
L: [a,b,c,q,p,r,s,t]
A: [a,b,c]
C(a): r
C(b): s
C(c): t
[r1]: p <- q,a
[r2]: q <- 
[r3]: r <- b,c
[r4]: t <- p,c
[r5]: s <- t
PREF: a > b
```

#### Format Explanation:

- **L:** Language - list all literals in square brackets
- **A:** Assumptions - list assumptions in square brackets
- **C(x): y** - Contrary mapping: the contrary of assumption x is y
- **[ruleName]: conclusion <- premise1, premise2** - Rules with optional premises
- **PREF: x > y** - Preference: x is preferred to y
  - You can also use: `a,b > c` meaning both a and b are preferred to c

### Features

1. **Automatic Conversion to Atomic ABA**
   - The system automatically converts your framework to atomic form

2. **Argument Generation**
   - Generates all valid arguments with their supports

3. **Attack Computation**
   - **Standard Attacks:** Basic ABA attacks (for reference)
   - **Normal Attacks:** ABA+ attacks respecting preferences
   - **Reverse Attacks:** ABA+ reverse attacks based on weak assumptions

4. **Visual Results**
   - Statistics dashboard
   - Complete list of arguments
   - Detailed attack descriptions

### Example Use Cases

#### Example 1: Simple Framework
```
L: [a,b,p,q]
A: [a,b]
C(a): q
C(b): p
[r1]: p <- a
[r2]: q <- b
PREF: a > b
```

#### Example 2: Complex Framework with Multiple Rules
```
L: [a,b,c,d,p,q,r,s]
A: [a,b,c,d]
C(a): p
C(b): q
C(c): r
C(d): s
[r1]: p <- a,b
[r2]: q <- c
[r3]: r <- d
[r4]: s <- p,q
PREF: a,b > c
PREF: c > d
```

## 🔧 Troubleshooting

### Build Fails
- Check that all files are in the correct structure
- Ensure `requirements.txt` is present
- Check Python version compatibility (Render uses Python 3.7+)

### Application Doesn't Load
- Check Render logs for errors
- Ensure the start command is `gunicorn app:app`
- Verify PORT environment variable is set (Render does this automatically)

### Results Not Displaying
- Check browser console for JavaScript errors
- Ensure proper input format
- Try with the default example first

## 📝 Notes

- **Free tier limitations:** Render's free tier spins down after 15 minutes of inactivity
- **Cold starts:** First request after inactivity may take 30-60 seconds
- **Upgrade option:** For production use, consider upgrading to a paid plan for always-on service

## 🎓 Academic Attribution

This application implements:
- **ABA (Assumption-Based Argumentation)** framework
- **ABA+ (ABA with Preferences)** with normal and reverse attacks
- Atomic conversion for structured argumentation
- Efficient