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

The examples/ directory contains sample files for testing, while the pyproject.toml explains all the required libraries to download.

| File Name	| Format |	Issue Type (what file lacks) |	Issue Severity |	Count (number of violations) | Score |
|-----------|-------|--------------------------------|-----------------|-------------------------------|-------|
| docx_Compliant|	docx |	None| None	|	0	| 100 |
|docx_altText1	|docx	Alternative text|	Minimal		|1|	76|
|docx_altText2|	docx|	Alternative text	|Intermediate	|	2|	53|
|docx_language|	docx|	Language set|	Minimal	|	1	|95|
|docx_heading|	docx|	Proper heading|	Minimal	|	1|	99|
|docx_table|	docx|	Tables with headers|	Minimal	|	1	|68|
|docx_list |	docx|	List format	|None	|	1	|100|
|docx_link	|docx|	Links have text to describe target|	None|		1	|100|
|docx_colorContrast	|docx|	Color contrast	|Severe	|	22	|5|
|docx_linkMore	|docx|	Links have text to describe target|	None	|	5	|100|
|docx_altTextMore|	docx	|Alternative text	|Intermediate|		5|	53|
|docx_tableMore|	docx|	Tables with headers	|Minimal	|	5|	68|
|docx_altText_heading |	docx	|Alternative text + Heading	|Minimal	|	2|	76|
|docx_table_contrast	|docx	|Tables with headers + Color contrast	|Minimal	|	2|	67|
|docx_decorativeImage	|docx|	Decorative Image	|Minimal	|	1	|76|
|docx_decorativeImage2	|docx|	Decorative Image|	Intermediate	|	2|	53|

### To run all examples --> python main.py --suite tests/                                                                         
### To run single document --> python main.py tests/document_name.pdf --fix
