from postprocess import generate_newsletter
from paper_summary_generator import run_generator

if __name__ == "__main__":
    run_generator(test=False)
    generate_newsletter()