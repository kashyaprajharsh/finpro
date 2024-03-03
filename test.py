chathistory = [
    ('Give me detail summary', 'I am sorry, but the answer to your question is not available in the context provided.'),
    ('Give me detail summary.', 'I am sorry, but the answer to your question is not available in the context provided.'),
    ('what is the report about?', "The report is about the financial results of Adani Enterprise for the fourth quarter and full year of fiscal 2023. The report includes information on the company's revenue, EBITDA, net income, and debt levels. The report also includes a discussion of the company's plans for the future, including its plans for capital expenditure and its plans for green hydrogen plants."),
    ('information on EBITDA', 'Q1. What is the EBITDA of incubating businesses?\nQ2. What is the EBITDA of operating business?\nQ3. What is the EBITDA of Carmichael Mines?\nQ4. What is the target for the production in the coming years?\nQ5. What is the revenue of Carmichael Mines?'),
    ('What is the EBITDA of incubating businesses?', '5,043 crores'),
    ('What is the EBITDA of Carmichael Mines?', 'The EBITDA of Carmichael Mines for Q4 FY23 is INR 780 crores.')
]

chat_dict_list = [{'prompt': prompt, 'response': response} for prompt, response in chathistory]

# Print the result
for chat_dict in chat_dict_list:
    print(chat_dict)
