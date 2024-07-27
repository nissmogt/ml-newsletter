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
    for root, _, files in os.walk(extract_path):
        print(f'Root: {root}\nFiles: {files}')
        if test:
            return next((Path(root) / file for file in files if file in ["test1.tex", "test2.tex"]), None)
        return next((Path(root) / file for file in files if file in ["arxiv.tex", "main.tex", "neurips_2024.tex"]), None)
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

def generate_formatted_summary(summary):
    prompt = (
        "Summarize the key points of a scientific article for a technical audience with these headings:\n\n"
        "**Objective:** \n**Method:** \n**Results:** \n**Significance:** "
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": summary}
        ]
    )
    formatted_summary = response.choices[0].message.content.strip()
    return {section.lower(): content.strip() for section, content in 
            (part.split(':', 1) for part in formatted_summary.split('**')[1:] if ':' in part)}

def template_newsletter(summary, paper):
    return f"**{paper['title']}**\n\n{summary}\n\narxiv: {paper['arxiv_url']}\n\n---\n\n"

def save_to_json(content, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)