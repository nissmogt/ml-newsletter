import os
import json
import arxiv
import tarfile
import datetime
from pathlib import Path
from functools import lru_cache
from pylatexenc.latex2text import LatexNodes2Text
import TexSoup as texsoup
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def initialize_directories(*dirs):
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

def fetch_latest_ml_papers(max_results=10, download=False, paperspath='', extension='tar.gz', subject_query='machine learning'):
    client = arxiv.Client()
    search = arxiv.Search(
        query=subject_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.LastUpdatedDate
    )
    paper_info = []
    list_of_files = []
    
    for result in client.results(search):
        print(f"MESSAGE -> Title: {result.title}")
        paper_info.append({
            "title": result.title,
            "date": result.published,
            "summary": result.summary,
            "authors": [str(author) for author in result.authors],
            "pdf_url": result.pdf_url,
            "arxiv_url": result.entry_id
        })
        fileout = f'{result.title.replace(":", "").replace(" ", "_")}.{extension}'
        print(f"MESSAGE -> Output File: {fileout}")
        list_of_files.append(fileout)
        if download:
            result.download_source(dirpath=paperspath, filename=fileout)
    return paper_info, list_of_files

def extract_tarfile(tar_file, extract_path):
    try:
        with tarfile.open(tar_file, 'r:gz') as tar:
            tar.extractall(path=extract_path)
        return True
    except tarfile.ReadError:
        print(f"Skipping {tar_file} as it is not a valid gzip file.")
        return False

def find_main_tex_file(extract_path, test=False):
    '''Find the main .tex file in the extracted directory
    '''
    for root, _, files in os.walk(extract_path):
        for file in files:
            if file.endswith('.tex'):
                with open(Path(root) / file, 'r') as f:
                    tex_content = f.read()
                if '\\begin{document}' in tex_content:
                    return Path(root) / file
    return None

@lru_cache(maxsize=32)
def parse_tex_file(file_path):
    with open(file_path, 'r') as file:
        tex_content = file.read()
    return texsoup.TexSoup(tex_content)

def find_tex_command(tex_soup, field):
    tex_list = tex_soup.find_all(field)
    if not tex_list:
        print(f'* Warning: "{field}" returned empty list!')
    return tex_list

def create_sections_from_main_tex(inputs_list, file_path):
    section_inputs = [inputs.contents[0] for inputs in inputs_list]
    print(f'Filepath: {file_path}\n\nContents: {section_inputs}')
    return [Path(file_path) / f"{y.replace('.tex', '')}.tex" for y in section_inputs]

def create_section_dict(section_filepaths):
    if not section_filepaths:
        print('** ERROR: section_filepaths is empty!')
        return None
    
    return {path.stem: parse_tex_file(str(path)) for path in section_filepaths}

@lru_cache(maxsize=32)
def generate_section_prompt(section_name):
    base_prompt = f"Create a detailed prompt to concisely summarize the '{section_name}' section of a scientific article. Stress that the summary must cover all key points but be concise, using markdown bullet points."
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": base_prompt},
            {"role": "user", "content": f"Generate a prompt for the '{section_name}' section."}
        ]
    )
    return response.choices[0].message.content.strip()

def section_summary_generator(section_dict):
    summaries = {}
    # Loop through each section and generate a summary
    for section_name, section_contents in section_dict.items():
        if 'math_definition' not in section_name and 'acknowledgements' not in section_name:
            print(section_name)
            text = str(section_contents)
            prompt = generate_section_prompt(section_name)
            print(f"PROMPT -> {prompt}")
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": text}
                    ]
                )
                # Checks to see if the response has any choices
                if response.choices:
                    summary = response.choices[0].message.content
                    print(f"SUMMARY -> {summary}")
                    summaries[section_name] = summary
                else:
                    print(f"**WARNING: No choices returned for section {section_name}")
            except Exception as e:
                print(f"**ERROR: {e}")

    return summaries 


def article_summary_generator(summary):
    prompt = (
        "Summarize the key points of a scientific article for a technical audience using the following format. "
        "Ensure you include exactly these headings and nothing else:\n\n"
        "## Objective:\nProvide a concise statement of the study's goal or main question.\n\n"
        "## Method:\nDescribe the main methods or procedures used in the study. Be explicit on the tools used.\n\n"
        "## Results:\nSummarize the key findings of the study.\n\n"
        "## Significance:\nExplain the importance and implications of the findings.\n\n"
        "Here is the summary to format:\n\n"
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that formats scientific article summaries."},
            {"role": "user", "content": prompt + summary}
        ],
        temperature=0.5,
        max_tokens=300
    )
    summary = response.choices[0].message.content.strip()
    return summary

def save_raw_summary(content, file):
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

def format_to_markdown(text):
    """Convert text to markdown format"""
    # Split text into sections
    text = text.strip()
    sections = text.split('##')
    sections = sections[1:]  # remove first empty element
    
    markdown_output = ""
    for section in sections:
        # Split the section into title and content based on Objective, Method, Results, Significance
        if 'Objective' in section:
            title = 'Objective'
            content = section.split('Objective:', 1)
        elif 'Method' in section:
            title = 'Method'
            content = section.split('Method:', 1)
        elif 'Results' in section:
            title = 'Results'
            content = section.split('Results:', 1)
        elif 'Significance' in section:
            title = 'Significance'
            content = section.split('Significance:', 1)
        else:
            print(f"**WARNING: Section not recognized: {section}")
            continue
        # Add title as h3 header
        markdown_output += f"### {title}\n\n"
        # Add the content and strip whitespace
        markdown_output += f"{content[1].strip()}\n\n"
    return markdown_output.strip()

def template_newsletter(summary, paper):
    return f"## {paper['title']}\n\n{summary}\n\narxiv: {paper['arxiv_url']}\n\n---\n\n"

# save to markdown
def save_newsletter(content, file):
    # content is a list with each element being a string
    with open(file, 'w+', encoding='utf-8') as f:
        for line in content:
            f.write(line)

def save_to_json(content, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)