import os
import json
import arxiv
import tarfile
import datetime
from pylatexenc.latex2text import LatexNodes2Text
import TexSoup as texsoup
from openai import OpenAI


OpenAI.openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

def fetch_latest_ml_papers(max_results=10, download=False, paperspath='', extension='tar.gz', subject_query='machine learning'):
    client = arxiv.Client()
    search = arxiv.Search(
        query=subject_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.LastUpdatedDate

    )
    paper_info = []
    list_of_files = []
    # print(f"Fetching papers from {days_ago} days ago...")
    for result in client.results(search):
        # only append if the paper was published more than 5 days ago
        # TODO: Add date range filter
        # print(f"Current date: {datetime.datetime.now().date()}")
        # print(f"Published date: {result.published.date()}")
        # delta_days = (datetime.datetime.now().date() - result.published.date()).days
        # print(delta_days)
        # if delta_days < days_ago:
            # continue
        print(f"MESSAGE -> Title: {result.title}")
        paper_info.append({
            "title": result.title,
            "date": result.published,
            "summary": result.summary,
            "authors": [str(author) for author in result.authors],
            "pdf_url": result.pdf_url,
            "arxiv_url": result.entry_id
        })
        fileout = f'{((result.title).replace(":", "")).replace(" ", "_")}.{extension}'
        print(f"MESSAGE -> Output File: {fileout}")
        list_of_files.append(fileout)
        if download:
            # result.download_pdf(dirpath=paperspath, filename=fileout)
            result.download_source(dirpath=paperspath, filename=fileout)
    return paper_info, list_of_files


def make_paper_dict(pdf_list, paperspath=''):
    paper_dict = {}
    for paper in pdf_list:
        paper_name = paper.split('_')[0].replace('-', '_').lower()
        paper = os.path.join(paperspath, paper)
        paper_dict[paper_name] = paper
    return paper_dict


def extract_tarfile(tar_file, extract_path):
    try:
        with tarfile.open(tar_file, 'r:gz') as tar:
            tar.extractall(path=extract_path)
    except tarfile.ReadError:
        print(f"Skipping {tar_file} as it is not a valid gzip file.")
        return False
    return True

def find_main_tex_file(extract_path):
    for root, dirs, files in os.walk(extract_path):
        for file in files:
            if file in ["arxiv.tex", "main.tex", "neurips_2024.tex"]:
                return os.path.join(root, file)
    return None


def parse_tex_file(file_path):
    with open(file_path, 'r') as file:
        tex_content = file.read()
    return texsoup.TexSoup(tex_content)


def find_tex_command(tex_soup, field):
    """ Wrapper for find_all TexSoup function. 
    """
    tex_list = tex_soup.find_all(field)
    if len(tex_list) > 0:
        return tex_list
    else:
        print(f'* Warning: "{field}" returned empty list!')
        return tex_list
    

def create_sections_from_main_tex(inputs_list, file_path):
    """ Creates a list of sections from the main TeX file.
    """
    section_inputs = [inputs.contents[0] for inputs in inputs_list]     # creates a list of the input sections
    print(f'Filepath: {file_path}\n\nContents: {section_inputs}')
    section_paths = [os.path.join(file_path, y.replace(".tex", "") + ".tex") for y in section_inputs]
    return section_paths

def create_section_dict(section_filepaths):
    """ Creates a Dictionary of Sections and their contents, based on a list of section file paths.
        Inputs:
                section_filepaths: List
        Outputs:
                sections_dic: Dictionary with 
                              key -> section name: Str
                              value -> section content: TexSoup Node
    """
    if not section_filepaths:
        print('** ERROR: section_filepaths is empty!')
        return None
    
    # TODO: Find out bottleneck
    sections_dic = {}
    for sec_file in section_filepaths:
        sec_name = os.path.splitext(os.path.basename(sec_file))[0]
        sections_dic[sec_name] = parse_tex_file(sec_file)
    return sections_dic


# def create_figure_dict(sections_dictionary, section='method'):
#     """Creates a dictionary of figures and their contents based on the sections dictionary for a specific section."""
#     if section not in sections_dictionary:
#         return None

#     sec = sections_dictionary[section]
#     fig_raw_list = find_tex_command(sec, 'includegraphics')
#     fig_content_list = find_tex_command(sec, 'figure')
    
#     if not fig_raw_list:
#         print(f'* Warning: {section} has no figures!')
#         return {}
    
#     figures_dic = {}
#     for fig_raw, fig_content in zip(fig_raw_list, fig_content_list):
#         fig_path = fig_raw[2]
#         fig_caption = fig_content.caption
#         fig_name = os.path.splitext(os.path.basename(fig_path))[0]
#         figures_dic[fig_name] = fig_caption

#     return figures_dic
    
# def compile_paper_figures(sec_dic):
#     """ Compiles all figures from every section into a dictionary.
#     """
#     paper_dict = {}
#     for sec_name, sec_content in sec_dic.items():
#         print(sec_name)
#         if 'math_definition' not in sec_name:
#             paper_dict[sec_name] = {
#                 "contents": sec_content,
#                 "figures": create_figure_dict(sec_dic, sec_name)
#             }
#     return paper_dict


# def count_figures(fd_list):
#     """ Test case that compares number of figure files with the number of figures found via TexSoup.
#     """
#     count = 0
#     for s in fd_list.items():
#         l = len(s[-1].keys())
#         if (l) > 0:
#             count += l
#     assert count == 8, f'{count} is not correct. Check files.'
#     print("test passed!")

def generate_section_prompt(section_name):
    # TODO: add Logging to this function
    base_prompt = f"You are a helpful assistant. Create a detailed prompt to concisely summarize the '{section_name}' section of a scientific article. In the prompt, stress that the summary must be detailed enough to cover all key points but concise enough to provide a clear understanding in markdown bullet point format."
    response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": base_prompt},
                    {"role": "user", "content": f"Generate a prompt for the '{section_name}' section."}
                ]
            )
    generated_prompt = response.choices[0].message.content.strip()
    return generated_prompt


def generate_formatted_summary(summary):
    prompt = (
        "You are a helpful assistant that summarizes the key points of a scientific article for a technical audience."
        "Generate a summary with the following headings: Objective, Method, Results, Significance.\n\n"
        "**Objective:** \n"
        "**Method:** \n"
        "**Results:** \n"
        "**Significance:** "
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": summary}
        ]
    )
    formatted_summary = response.choices[0].message.content.strip()
    # Extract the individual sections from the summary text
    sections = formatted_summary.split("**")
    summary_dict = {}
    for idx, section in enumerate(sections):
        if "Objective:" in section:
            summary_dict["objective"] = sections[idx+1].strip()
        elif "Method:" in section:
            summary_dict["method"] = sections[idx+1].strip()
        elif "Results:" in section:
             summary_dict["results"] = sections[idx+1].strip()
        elif "Significance:" in section:
            summary_dict["significance"] = sections[idx+1].strip()

    return summary_dict


def template_newsletter(summary, paper):

    newsletter = f"**{paper['title']}**\n\n"
    newsletter += summary + "\n\n"
    newsletter += f"arxiv: {paper['arxiv_url']}\n\n"
    newsletter += "---\n\n"
    return newsletter


def save_to_json(content, file_path):
# Function to save content to a JSON file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)
