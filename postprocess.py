import argparse
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
    <title>Weekly Machine Learning Research Highlights</title>
    <link href={font} rel="stylesheet">
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div>
        <h1>newsletter mehrabiani</h1>
        <nav>
            <div class="links-container">
                <a href="/" class="home-link">home</a>
                <a href="/about.html" class="home-link">about</a>
                <a href="/blog.html" class="home-link">blog</a>
                <a href="/newsletter.html" class="home-link">newsletter</a>
            </div>
        </nav>
    </div>
            
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
        <h2>Updates on Friday.</h2>
        <p>updated: {date}</p>
        <p>Click titles below to view article summaries. Generated using a custom pipeline with OpenAI's <strong>gpt-4o-mini</strong>.</p>
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