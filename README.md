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

The examples/ directory contains sample files for testing, while the requirements.txt explains all the required libraries to download.

### To run all examples --> python main.py --suite tests/                                                                         
### To run single document --> python main.py tests/document_name.pdf --fix
