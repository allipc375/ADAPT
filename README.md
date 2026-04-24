# Accessibility-Diagnostics-and-Auto-Patching-Tool-ADAPT-

The Web Contact Accessibility Guidelines (WCAG) 2.2 are the most recent federal accessibility standards for digital content and documents. The regulations on alternative text, color contrast, headings, and other areas allow people with cognitive and visual disabilities to have access to web content. ​

Ally is an add-in for the Canvas Learning Management System that is intended to process Canvas documents and score them for accessibility based on the WCAG 2.2 guidelines, in which the specific violations are listed for the user to fix. However, the Ally system is currently limited by:​

  1) Being usable only through files uploaded into Canvas​
  2) Requiring manual user interaction to determine scores​ and corrective actions​
  3) Necessitating cycles of offline edit and manual ​upload to confirm that corrective actions have the​ intended effect

       
## Objectives:

- Generate a benchmark set of files with a range of WCAG 2.2 accessibility issues and corresponding scores.
- Develop an alternative to the Ally scoring system that can be run outside of Canvas for differing document types (PDF, Microsoft Office DOCX, Presentation PPTX)
- Based on the scoring system developed, make fixes to all WCAG 2.2 accessibility violations (color contrast, alternative text, table headers, language settings, etc.)​


## Conclusion/Results:

Using the benchmark and alternative scoring method as a base, we developed an automated tool for accessibility diagnosis and scoring of common document types of PDF, PPTX, and DOCX. This was then extended as a framework for fully automated patching of accessibility issues. Our initial prototype indicates that addressing common WCAG 2.2 compatibility issues can be automated with minimal user interaction. ​​

This program is a prototype framework for fully automated patching of accessibility issues for PDF, DOCX, and PPTX documents based on WCAG 2.2 Guidelines. The program was made for the Symposium on Undergraduate Research and Creatuve Activity at Iowa State University. There is a main.py, a checker.py, and 3 fixers and checkers for the different file types. Currently single files or a test suite can be run.

The tests/ directory contains sample files for testing, while the pyproject.toml explains all the required libraries to download.

| File Name	| Format |	Issue Type (what file lacks) |	Issue Severity |	Count (number of violations) | Score |
|-----------|-------|--------------------------------|-----------------|-------------------------------|-------|
|docx_test001	|docx|	Alternative text|	Minimal		|1|	76|
|docx_test002|	docx|	Alternative text	|Intermediate	|	2|	53|
|docx_test003|	docx	|Alternative text	|Intermediate|		5|	53|
|docx_test004 |	docx	|Alternative text + Heading	|Minimal	|	2|	76|
|docx_test005	|docx|	Color contrast	|Minimal	|	1	|76|
|docx_test006	|docx|	Color contrast	|Intermediate	|	2	|53|
|docx_test007	|docx|	Color contrast	|Severe	|	22	|5|
|docx_test008	|docx|	Decorative Image	|Minimal	|	1	|76|
|docx_test009|	docx|	Proper heading|	Minimal	|	1|	99|
|docx_test010	|docx|	Links have text to describe target|	None|		1	|100|
|pdf_test001	|pdf	|None	|None	|0	|100|
|pdf_test002|	pdf	|Language set|	Minimal	|1|	100	|
|pdf_test003|	pdf	|Links have text to describe target	|None|	1	|100|
|pdf_test004	|pdf	|List format	|None	|1	|100	|
|pdf_test005	|pdf	|Tables with headers	|Minimal	|1	|68	|	
|pdf_test006	|pdf |Tables with headers + Color contrast	|Minimal|	2	|98	|
|pdf_test007|	pdf	|Tagging pdf	|Severe	|1|	7		|
|pdf_test008	|pdf|	Alternative text|	Minimal	|1	|77	|																			
|pdf_test009|	pdf	|Alternative text|	Intermediate	|2	|54		|
|pdf_test010|	pdf|	Alternative text	|Intermediate	|5	|54	|
|pdf_test011|	pdf	|Color contrast|	Severe	|22	|5	|
|pptx_test001|	pptx	|None|	None|	0	|100	|
|pptx_test002|	pptx	|Alternative text	|Minimal	|1	|84	|																			
|pptx_test003	|pptx|	Alternative text|	Intermediate	|2	|53		|
|pptx_test004|	pptx	|Color contrast|	Minimal|	2|	86	|																			
|pptx_test005	|pptx	|Color contrast	|Intermediate|	7	|48|
|pptx_test006|	pptx|	Color contrast	|Intermediate	|5|	53|
|pptx_test007	|pptx	| Text on image|	None|	0|	100		|		
|pptx_test008|	pptx|	Title slide	|None	|0	|100	|																			


### To run all examples --> python main.py --suite tests/                                                                         
### To run single document --> python main.py tests/document_name.pdf --fix
