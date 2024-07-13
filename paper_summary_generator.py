import os
import time
from datetime import datetime
from openai import OpenAI
from utils import (
    fetch_latest_ml_papers, extract_tarfile, find_main_tex_file, parse_tex_file,
    find_tex_command, create_sections_from_main_tex, create_section_dict,
    generate_section_prompt, generate_formatted_summary, save_to_json
)

# Initialize OpenAI client
client = OpenAI()
paperspath = './papers'
newsletter_dir = './newsletter'

if not os.path.exists(paperspath):
    os.makedirs(paperspath)
if not os.path.exists(newsletter_dir):
    os.makedirs(newsletter_dir)


# Fetch the latest ML papers and download them
paper_info_list, paper_source_folder_list = fetch_latest_ml_papers(max_results=10, days_ago=5, download=True, 
                                                                   paperspath=paperspath, extension='tar.gz', 
                                                                   subject_query='machine learning')

# Initialize the newsletter content
newsletter_content = {
    "newsletter_title": "Weekly Machine Learning Research Highlights\n\n",
    "papers": []
}

# Process each paper
count = 0
for idx, paper in enumerate(paper_info_list):
    tar_file = os.path.join(paperspath, paper_source_folder_list[idx])
    extract_path = os.path.join(paperspath, paper_source_folder_list[idx].replace('.tar.gz', ''))
    if not extract_tarfile(tar_file, extract_path):
        continue
    
    main_text = find_main_tex_file(extract_path)
    # if main_text is None then skip to next paper
    if main_text is None:
        print(f"Main tex file not found for {paper['title']}\nmoving on to next paper...")
        continue
    print(f"Main text file: {main_text}")
    tex_soup = parse_tex_file(main_text)
    
    print(f"Title: {paper['title']}")
    
    input_list = find_tex_command(tex_soup, 'input')
    print(input_list)
    
    section_filepaths = create_sections_from_main_tex(input_list, extract_path)
    section_dict = create_section_dict(section_filepaths)
    
    # if section_dict is empty then skip to next paper
    if not section_dict:
        print(f"No sections found for {paper['title']}\nmoving on to next paper...")
        continue
    print(section_dict.keys())
    
    summaries = {}
    for section_name, section_contents in section_dict.items():
        if 'math_definition' or 'acknowledgements' not in section_name:
            print(section_name)
            text = str(section_contents)
            prompt = generate_section_prompt(section_name)
            # print(f"PROMPT -> {prompt}")
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ]
            )
            summary = response.choices[0].message.content
            #print(f"SUMMARY -> {summary}")
            summaries[section_name] = summary
    concat_summary = "\n".join(f"- {summary}" for summary in summaries.values())
    formatted_summary = generate_formatted_summary(concat_summary)
    # Add the details of the current paper to the newsletter data
    paper_summary = {
        "title": paper['title'],
        "objective": formatted_summary.get("objective", ""),
        "method": formatted_summary.get("method", ""),
        "results": formatted_summary.get("results", ""),
        "significance": formatted_summary.get("significance", ""),
        "arxiv": paper['arxiv_url']
    }
    newsletter_content["papers"].append(paper_summary)
    count += 1

print(f"*** Final Newsletter Papers: {count}")
# print(newsletter_content)

# Create a folder within the newsletter directory for the current year and then use current date as json output file name
current_year = datetime.now().year
current_date = time.strftime("%Y-%m-%d")
json_output_folder = os.path.join(newsletter_dir, str(current_year))
# check if the folder for the current year exists, if not create it
if not os.path.exists(json_output_folder):
    os.makedirs(json_output_folder)
json_file_path = os.path.join(json_output_folder, f"n_{current_date}.json")
# Save the newsletter content to the JSON file
save_to_json(newsletter_content, json_file_path)