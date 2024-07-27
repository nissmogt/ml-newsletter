import time
from datetime import datetime
from openai import OpenAI
from pathlib import Path
from utils import (
    initialize_directories, fetch_latest_ml_papers, extract_tarfile, find_main_tex_file, parse_tex_file,
    find_tex_command, create_sections_from_main_tex, create_section_dict,
    section_summary_generator, article_summary_generator, template_newsletter, save_raw_summary,
    format_to_markdown, save_newsletter 
)

BASE_DIR = Path(__file__).resolve().parent
PAPERS_DIR = BASE_DIR / 'papers'
NEWSLETTER_DIR = BASE_DIR / 'newsletter'
SUMMARY_DIR = BASE_DIR / 'summary_cache'
TEST_DIR = BASE_DIR / 'test'

def generate_newsletter_content(paper_info_list, paper_source_folder_list, papers_path, test=False):
    client = OpenAI()
    print(f"*** Number of Papers: {len(paper_info_list)}")
    print(f"*** Papers Path: {papers_path}")
    print(f"*** Paper Info List: {paper_info_list}")
    print(f"*** Mode: {['Test' if test else 'Production']}")

    newsletter_content = ["# Weekly Machine Learning Research Highlights\n\n"]
    
    for idx, paper in enumerate(paper_info_list):
        tar_file = papers_path / paper_source_folder_list[idx]
        extract_path = papers_path / paper_source_folder_list[idx].replace('.tar.gz', '')
        print(f"\n\n**Extract Path: {extract_path}")
        
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
        
        summaries = section_summary_generator(section_dict)

        # Join all the summaries into a single string, put into json format, and add to newsletter content
        concat_summary = "\n".join(f"{summary}" for summary in summaries.values())
        summary = article_summary_generator(concat_summary)
        formatted_summary = format_to_markdown(summary)
        # Cache the raw summary
        cdate = time.strftime("%Y-%m-%d")
        SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
        save_raw_summary(formatted_summary, SUMMARY_DIR / f"{cdate}_{paper['title']}.md")
        news_template = template_newsletter(formatted_summary, paper)
        save_newsletter(news_template, SUMMARY_DIR / f"{cdate}.md")

        newsletter_content += news_template
    print(f"*** Final Newsletter Papers: {len(newsletter_content)}")
    return newsletter_content

def main(test=False):
    # Initialize directories
    papers_dir = TEST_DIR if test else PAPERS_DIR
    initialize_directories(papers_dir, NEWSLETTER_DIR)

    if not test:
        # Fetch latest machine learning papers
        n_papers = 5
        paper_info_list, paper_source_folder_list = fetch_latest_ml_papers(
            max_results=n_papers, download=True, 
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
    output_folder = NEWSLETTER_DIR / str(current_year)
    output_folder.mkdir(parents=True, exist_ok=True)
    file_path = output_folder / f"n_{current_date}.md"
    save_newsletter(newsletter_content, file_path)

if __name__ == "__main__":
    main(test=False)  # Set to True for testing