import re
import os
from datetime import datetime


def generate_newsletter():
    BASE_NEWSLETTER_FOLDER = os.path.join("newsletter")
    current_date = datetime.now().strftime("%Y-%m-%d")
    markdown_file = os.path.join(BASE_NEWSLETTER_FOLDER, "2024", f"n_{current_date}.md")
    
    try:
        # Read the markdown file
        with open(markdown_file, 'r', encoding='utf-8') as file:
            markdown_content = file.read()
        
        # Convert markdown to HTML
        html_content = markdown_to_html(markdown_content, date=current_date)
        font = "https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&display=swap"
        
        # Create the full HTML document
        full_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Newsletter Mehrabiani</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="{font}" rel="stylesheet">
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
    <header>
        <h1>newsletter mehrabiani</h1>
        <nav>
            <input type="checkbox" id="sidebar-active">
            <label for="sidebar-active" class="open-sidebar-button">
                <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#000000"><path d="M120-240v-80h720v80H120Zm0-200v-80h720v80H120Zm0-200v-80h720v80H120Z"/></svg>
            </label>
            <label id="overlay" for="sidebar-active"></label>
            <div class="links-container">
                <label for="sidebar-active" class="close-sidebar-button">
                    <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#000000"><path d="m256-200-56-56 224-224-224-224 56-56 224 224 224-224 56 56-224 224 224 224-56 56-224-224-224 224Z"/></svg>
                </label>    
                <a class="home-link" href="/">home</a>
                <a class="home-link" href="/about.html">about</a>
                <a class="home-link" href="/blog.html">blog</a>
                <a class="home-link" href="/newsletter.html">newsletter</a>
            </div>
        </nav>
    </header>
            {html_content}
    <footer>
        <a href="https://github.com/nissmogt" class="footer-link">github</a> |
        <a href="https://linkedin.com/in/kareemmehrabiani" class="footer-link">linkedin</a> |
        <a href="mailto:kareem@mehrabiani.com" class="footer-link">email</a>
        <p class="copyright">Copyright 2024</p>
    </footer>
</body>
</html>
        """
        
        # Save the newsletter
        newsletter_path = os.path.join(BASE_NEWSLETTER_FOLDER, "html", f"final_newsletter_{current_date}.html")
        with open(newsletter_path, "w", encoding='utf-8') as f:
            f.write(full_html)
        
        print(f"Newsletter generated successfully: {newsletter_path}")
        
    except Exception as e:
        print(f"Error generating newsletter: {e}")


def markdown_to_html(markdown_content, date=None):
    if date is None:
        date = datetime.now().strftime("%B %d, %Y").lower()

    # Split the content into sections
    sections = re.split(r'\n---\n', markdown_content)

    html_content = f"""
    <div class="container">
        <h1>Weekly Machine Learning Research Highlights 🤖</h1>
        <h2>
            Updates on Friday.
            <p>updated: {date}</p> </br> 
            Click titles below to view article summaries. Generated using a custom pipeline with OpenAI's <strong>gpt-4o-mini</strong>.
        </h2>
    """

    for section in sections:
        section = section.strip()
        if not section:
            continue

        lines = section.strip().split('\n')
        title = lines[0].strip('##').strip()
        content = '\n'.join(lines[1:])

        # Extract arxiv link
        arxiv_match = re.search(r'arxiv:\s*(http://arxiv\.org/\S+)', content)
        arxiv_link = arxiv_match.group(1) if arxiv_match else ''
        
        # Remove ArXiv link from content
        content = re.sub(r'arxiv:\s*http://arxiv\.org/\S+', '', content).strip()

        html_content += f"""
        <details>
            <summary>{title}</summary>
            <div class="newsletter">
                {convert_markdown_section(content)}
                <p><a href="{arxiv_link}" target="_blank">ArXiv Link</a></p>
            </div>
        </details>
        """

    html_content += "</div>"
    return html_content


def convert_markdown_section(markdown):
    # Convert headers
    markdown = re.sub(r'^###\s*(.*?)$', r'<strong>\1</strong>', markdown, flags=re.MULTILINE)
    
    # Convert bold
    markdown = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', markdown)
    
    # Convert italic
    markdown = re.sub(r'\*(.*?)\*', r'<em>\1</em>', markdown)
    
    # Convert links
    markdown = re.sub(r'\[(.*?)\]\(((?!http://arxiv\.org).*?)\)', r'<a href="\2">\1</a>', markdown)

    # Handle inline TeX
    markdown = re.sub(r'\$(.+?)\$', r'\\(\1\\)', markdown)
    # Handle display TeX
    markdown = re.sub(r'\$\$(.*?)\$\$', r'\\[\1\\]', markdown, flags=re.DOTALL)
    
    # Convert paragraphs
    markdown = markdown.replace('\n\n', '</p><p>')
    markdown = f'<p>{markdown}</p>'
    
    return markdown

# Test using a markdown string
def test1():
    markdown = """
    # Hello, World!

    This is a **markdown** file. Here is a link to [Google](https://www.google.com).

    - Item 1
    - Item 2
    - Item 3
    """
    print(markdown_to_html(markdown))

# Test 2 load a markdown file
def test2():
    with open('test_newsletter.md', 'r') as f:
        markdown = f.read()
    print(markdown_to_html(markdown))

# use argparse to convert markdown file to html
# if __name__ == '__main__':
#     parser = argparse.ArgumentParser(description='Convert markdown to HTML')
#     parser.add_argument('file', type=str, help='Path to the markdown file')
#     args = parser.parse_args()
#     with open(args.file, 'r') as f:
#         markdown = f.read()
#     # save to html file and format accordingly
#     with open('md_to_output.html', 'w') as f:
#         f.write(markdown_to_html(markdown))