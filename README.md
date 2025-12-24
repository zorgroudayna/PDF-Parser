# Fitz PDF Parser
**Introduction**

A Python-based PDF parser that extracts structured information from PDFs, including headers, table data, and anchor values. Built with PyMuPDF (fitz), it automatically detects headers, identifies table columns, and organizes words into structured outputs.

**Features**

 1.Extracts words and text spans from PDF pages. 
 
 2.Detects headers using predefined keywords (e.g., Date, Opération, Débit, Crédit).
 
 3.Identifies table columns and assigns words to headers.
 
 4.Detects anchor values (such as monetary amounts) in tables.

**How it Works**

 1. Extract Words: All text spans are captured with position, font, size, and color.
 2.Detect Headers: Predefined keywords are matched and stored with their positions.

     <img width="600" height="498" alt="image" src="https://github.com/user-attachments/assets/5c99c557-cc43-455b-be5b-6175abf9bdc7"  />
 
 3. Detect Columns: Table columns are automatically detected by analyzing word positions.

    <img width="600" height="520" alt="image" src="https://github.com/user-attachments/assets/e27ad388-4aa0-4d26-ad4b-b436b8a1a2d5"  />
  
 5. Assign Headers: content in table zones are assigned to the closest header or anchor value.

    <img width="600" height="503" alt="image" src="https://github.com/user-attachments/assets/1be5bece-1fd9-4bb7-b2ff-87590c433783"  />
 









