import time
from datetime import datetime
from openai import OpenAI
from pathlib import Path
from utils import (
    initialize_directories, fetch_latest_ml_papers, extract_tarfile, find_main_tex_file, parse_tex_file,
    find_tex_command, create_sections_from_main_tex, create_section_dict,
    generate_section_prompt, generate_formatted_summary, save_to_json
)

BASE_DIR = Path(__file__).resolve().parent
PAPERS_DIR = BASE_DIR / 'papers'
NEWSLETTER_DIR = BASE_DIR / 'newsletter'
TEST_DIR = BASE_DIR / 'test'

def generate_newsletter_content(paper_info_list, paper_source_folder_list, papers_path, test=False):
    client = OpenAI()
    print(f"*** Number of Papers: {len(paper_info_list)}")
    print(f"*** Papers Path: {papers_path}")
    print(f"*** Paper Info List: {paper_info_list}")
    print(f"*** Mode: {['Test' if test else 'Production']}")

    newsletter_content = {
        "newsletter_title": "Weekly Machine Learning Research Highlights\n\n",
        "papers": []
    }
    
    for idx, paper in enumerate(paper_info_list):
        tar_file = papers_path / paper_source_folder_list[idx]
        extract_path = papers_path / paper_source_folder_list[idx].replace('.tar.gz', '')
        print(f"**Extract Path: {extract_path}")
        
        if not extract_path.exists():
            extract_tarfile(tar_file, extract_path)
        else:
            print(f"**INFO: {paper['title']} already extracted.")

        main_text = find_main_tex_file(extract_path, test=test)
        if main_text is None:
            print(f"**WARNING: Main tex file not found for {paper['title']}\nmoving on to next paper...")
            continue
        
        print(f"Main text file: {main_text}")
        tex_soup = parse_tex_file(main_text)
        print(f"Title: {paper['title']}")
        
        input_list = find_tex_command(tex_soup, 'input')
        print(input_list)
        
        section_filepaths = [main_text] if not input_list else create_sections_from_main_tex(input_list, extract_path)
        section_dict = create_section_dict(section_filepaths)
        
        if not section_dict:
            print(f"**WARNING: No sections found for {paper['title']}\nmoving on to next paper...")
            continue
        print(section_dict.keys())
        
        summaries = {}  # Dictionary to store summaries for each section
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

        # Join all the summaries into a single string, put into json format, and add to newsletter content
        concat_summary = "\n".join(f"- {summary}" for summary in summaries.values())
        formatted_summary = generate_formatted_summary(concat_summary)
        paper_summary = {
            "title": paper['title'],
            "objective": formatted_summary.get("objective", ""),
            "method": formatted_summary.get("method", ""),
            "results": formatted_summary.get("results", ""),
            "significance": formatted_summary.get("significance", ""),
            "arxiv": paper['arxiv_url']
        }
        newsletter_content["papers"].append(paper_summary)

    print(f"*** Final Newsletter Papers: {len(newsletter_content['papers'])}")
    return newsletter_content

def main(test=False):
    # Initialize directories
    papers_dir = TEST_DIR if test else PAPERS_DIR
    initialize_directories(papers_dir, NEWSLETTER_DIR)

    if not test:
        # Fetch latest machine learning papers
        paper_info_list, paper_source_folder_list = fetch_latest_ml_papers(
            max_results=5, download=True, 
            paperspath=papers_dir, extension='tar.gz', 
            subject_query='machine learning'
        )
    else:
        # Test data
        paper_info_list = [
            {'title': 'Sample Paper 1', 'arxiv_url': 'http://arxiv.org/'},
            {'title': 'Sample Paper 2', 'arxiv_url': 'http://arxiv.org/'}
        ]
        paper_source_folder_list = ['test1', 'test2']

    newsletter_content = generate_newsletter_content(paper_info_list, paper_source_folder_list, papers_dir, test=test)

    current_year = datetime.now().year
    current_date = time.strftime("%Y-%m-%d")
    json_output_folder = NEWSLETTER_DIR / str(current_year)
    json_output_folder.mkdir(parents=True, exist_ok=True)
    json_file_path = json_output_folder / f"n_{current_date}.json"
    save_to_json(newsletter_content, json_file_path)

if __name__ == "__main__":
    main(test=True)  # Set to True for testing