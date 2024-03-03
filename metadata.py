import os

main_folder = "E:\earning_reports_copilot\Concalls"
metadata_list = []

for company_folder in os.listdir(main_folder):
    company_path = os.path.join(main_folder, company_folder)
    
    if os.path.isdir(company_path):
        for pdf_file in os.listdir(company_path):
            if pdf_file.endswith(".pdf"):
                # Create metadata entry
                metadata = {
                    "source": os.path.join(company_path, pdf_file)
                }
                
                # Add to metadata list
                metadata_list.append(metadata)

# Print the resulting metadata list
for entry in metadata_list:
    print(entry)
