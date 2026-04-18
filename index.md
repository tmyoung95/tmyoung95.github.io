---
layout: default
title: Home
---

# > tyler_young

computer science capstone portfolio

---

## > professional_self_assessment

Completing this program and building this ePortfolio helped me understand how to apply what I learned in a practical way and most importantly, how to integrate these skills to fulfill needs in specific professional environments. Initially, I focused on how the original dashboard could be improved to fit a real world use case, and over time I shifted to optimizing routines I was already familiar with in my professional experience . This portfolio reflects that shift and shows how I approach development with a focus on solving real problems with a surgical attention to detail to make programs that are easy to use, maintain, and scale as need be.

Throughout the program, I developed stronger skills in collaboration and communication. Working in group environments taught me how to stay organized, rely on others, and document processes for seamless communication and task distribution. I became more adept at recognizing strengths, weaknesses, and opportunities for growth, and leveraged all three to ensure each iteration of development optimized the wellbeing of the project as well as the wellbeing of all team members.  I also became more comfortable explaining technical concepts in a clear way, especially to non-technical audiences, which is important when working with stakeholders who need to understand what a system does and why it matters.

I also built a stronger foundation in data structures and algorithms. Instead of only focusing on whether something works, I started thinking about how data is organized and how it flows through a system. This changed how I approach problem solving and helped me build solutions that are more consistent and easier to maintain. Throughout the development of this project, I made sure to think of all ways that the data collected could be utilized for better organization and program flexibility to accomodate a multitude of use cases. 

My experience with software engineering and databases helped me understand how to design applications in a structured and organized way. I learned how to separate logic into different parts so the system is easier to manage and scale, and I became more comfortable working with stored data, queries, and user input. These skills are important when building applications that need to handle real data reliably.

Security is now something I consider a critical element of the development process rather than a featurer. I learned to think about how systems can be misused and how to prevent that through proper validation, controlled access, and safer handling of sensitive data. This alone inspired my firsst attempt at an MFA system and RBAC structures to ensure that data was as protected as possible. Throughout this porject, I was aware of my responsibilites as a developer to the end user and their data, understanding that computer scientists and software engineers must consider the consequences of poorly secured programs and the user's right to privacy.  

The artifacts in this portfolio reflect these skills across different areas of computer science. Each one focuses on a specific aspect of development, including system design, working with data and algorithms, and managing, storing, and validating information. Together, they show how I build applications that are structured, functional, and aligned with real world needs. The sections that follow provide the technical details and examples that support these skills and demonstrate my overall growth as a developer.

---

## > code_review

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">
  <iframe
    src="https://www.youtube.com/embed/WwcLFoeCDaw"
    title="Code Review Video"
    style="position: absolute; top:0; left:0; width:100%; height:100%; border:0;"
    allowfullscreen>
  </iframe>
</div>
---

## > artifacts

<p>
  All original and enhancement artifacts can be retrieved at the following repository link:
  <a href="https://github.com/tmyoung95/tmyoung95.github.io" target="_blank">
    GitHub Repository
  </a>
</p>

The original artifact for all three enhancements was the CS-340 Animal Shelter Dashboard App originally developed in June of 2025. At a high level, the artifact was a dashboard that utilized a Python CRUD module that connected to a Mongo DB database that allowed users to visualize animal rescue data and pinpoint where certain animals were being held on a map.

### enhancement_1 : software design and engineering

This artifact was selected for this enhancement due to its glaring security issues. Primarily, the original artifact contained hardcoded credentials for access, which was identified as a major security risk. The most important components of this artifact that showcase my skills are the authentication flow and the integration of multi factor authentication into the login process. This required restructuring how the application handles user sessions, adding a second verification step, and ensuring that users cannot access the dashboard without successfully completing both authentication steps. I also implemented basic role-based access control, which introduces different levels of permission within the application, namely, a read-only permission that will be unable to manipulate data in the case where a user just needs to visualize the data instead of manipulating it. Though the data privileges will be more apparent in the milestone 3 enhancement, this reflects how real systems restrict access based on user roles and responsibilities. Compared to the original version of the artifact, the enhanced version is significantly more secure and more aligned with modern software development standards. While the original application focused primarily on displaying data, the updated version introduces proper access control and authentication checks, making it more representative of a real-world professional system.

In terms of course outcomes, this enhancement primarily supports outcome five, which focuses on developing a security mindset. By implementing MFA, I demonstrated an understanding of layered authentication and the importance of protecting systems from unauthorized access. I also worked toward outcome one through the role-based system, which allows different types of users to interact with the application in a controlled way. Outcome four is also partially demonstrated through the use of Python and Dash to implement a functional authentication system. 
	
Working on this enhancement helped me understand how real authentication systems work beyond just a basic username and password. One of the biggest things I learned was how multi-factor authentication actually functions. By using the PyOTP library, I implemented time-based one-time passwords (TOTP), which are generated from a shared secret and change every few seconds (Pyotp, 2023). This showed me how systems can add an extra layer of security by requiring something the user has (an authenticator app) in addition to something they know (their password). I also learned the importance of handling passwords securely. Instead of storing passwords directly, I used the Werkzeug library to hash and verify them. This reinforced the idea that sensitive data should never be stored in plain text and that proper security practices need to be built into the system from the start (Workzeug, n.d.). One of the biggest challenges I faced was managing the different steps in the authentication process. Unlike a simple login system, this required handling account creation, MFA setup, and verification as separate stages. I ran into many issues where the application would move to the wrong step or log a user out when setting up other users. Fixing these problems helped me better understand how application flow works and how important it is to control the app state carefully. Another challenge was making sure the system handled errors correctly. For example, things like mismatched passwords or incorrect MFA codes needed to show proper messages instead of generating callback errors within the Dash framework. This forced me to pay more attention to validation and error handling, which is something very important for any project I work on. This enhancement also demonstrated the importance of testing frequently and accounting for edge cases. 

<p><strong>References</strong></p>

<ul>
  <li>
    <a href="https://pypi.org/project/pyotp/" target="_blank">
      Python Package Index. (2023, July 27). PyOTP 2.9.0 – PyPI
    </a>
  </li>
  <li>
    <a href="https://werkzeug.palletsprojects.com/en/stable/utils/" target="_blank">
      Werkzeug. (n.d.). Utilities — Werkzeug Documentation (3.1.x)
    </a>
  </li>
</ul>


### enhancement_2 : algorithms and data structures

This artifact was selected for this enhancement because the while the original application merely displayed location data, it didn’t do anything useful with it other than let the user know the geographic location of an animal. In my conversion of the original artifact into an insurance risk exposure dashboard, I utilized my experience in the insurance field to perform a very useful function in displaying the distance to coast and risk categorization of a policy. The most important components of this artifact that showcase my skills are the implementation of the distance-to-coast calculation and the integration of a structured policy data system. The distance calculation takes a property’s latitude and longitude, finds the closest point on the coastline shape sourced from Natural Earth, and converts that into miles to determine a risk zone like Coastal, Midland, or Inland (Natural Earth, n.d.). This shows my ability to take an industry specific problem and turn it into a working solution using algorithms. I also built out a structured data system using pandas and SQLite, which allows the app to store and process policy data in a clean and organized way. I added a full policy input form with validation to perform an instance of the distance to coast algorithm, and enhancement 3 (databases) will allow for bulk insertion and individual deletion and editing of policies when implemented. Compared to the original version of the artifact, this version actually processes location data and performs more complex functions with it to provide users with utility, especially in a field where older legacy versions force the user to rely on third party tools to do the same. 

In terms of course outcomes, this enhancement primarily supports outcome two, which focuses on implementing algorithms and working with data structures. The distance-to-coast calculation is a direct example of building and applying an algorithm using coordinate-based data. I also worked toward outcome four through the use of Python tools like pandas, geopandas, and shapely to handle and process data within the application. Outcome one is also supported through the way data moves through the system, from user input, through validation, into storage, and then into calculated results shown on the dashboard. 

Working on this enhancement helped me understand how to perform algorithmic processes to geometric data using Shapely (DiTect, n.d.). I also got a lot more comfortable working with dataframes using pandas, especially when adding new fields without breaking everything else (W3Schools.com, n.d.). One of the biggest challenges I faced was integrating all of this into an already complicated app. Since I already had authentication and role-based access in place, adding forms, database updates, and calculations made the callback logic complicated fast. I ran into a lot of issues with Dash callbacks, especially duplicate outputs and getting forms to show and hide correctly. Fixing that helped me better understand the importance of clean formatting and considering the user experience when developing an application. Another challenge was making sure validation errors didn’t crash the app and instead showed clean messages to the user. 

<p><strong>References</strong></p>
<ul>
  <li>
    <a href="https://www.iditect.com/faq/python/coordinates-of-the-closest-points-of-two-geometries-in-shapely.html" target="_blank">
      DiTect. (n.d.). Coordinates of the closest points of two geometries in Shapely
    </a>
  </li>
  <li>
    <a href="https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-coastline/" target="_blank">
      Natural Earth. (n.d.). Coastline - Free vector and raster map data at multiple scales
    </a>
  </li>
  <li>
    <a href="https://www.w3schools.com/python/pandas/pandas_dataframes.asp" target="_blank">
      W3Schools. (n.d.). Pandas DataFrames
    </a>
  </li>
</ul>

### enhancement_3 : databases

This artifact was selected for this enhancement because while the original application retrieved and displayed data, it lacked more intuitive means of adding files and performing more intricate querying for filters. I implemented a SQLite database and created a structured policy data system that allows the application to store and manage its own data (GeeksforGeeks, 2025). The most important components of this artifact that showcase my skills are the database system and the separation of logic into files like database.py and validation.py. The database.py file handles storing and retrieving policy records, while validation.py makes sure all user input is clean and valid before being saved. This shows my ability to keep code organized and easier to work with. I also added a policy input form that connects directly to the database so users can create new records. In addition to the single policy addition form, I added the ability to upload a CSV file, where duplicate policy numbers are skipped so the database does not store duplicates. I also added query based filters so users can view data by things like state and county, which makes the dashboard more useful. Compared to the original version, this version can store, manage, and filter its own data instead of just displaying what already exists, which makes it much more useful in an industry specific setting. 

In terms of course outcomes, this enhancement primarily supports outcome one, which focuses on building systems that allow users to interact with data in a way that supports decision making. By allowing users to input, store, and view policy data within the application via multiple ways (CSV and single input), the dashboard becomes a more useful tool to visualize important data that may influence organizational decisions. I also worked toward outcome four through the use of Python, SQLite, and modular design to create a working system that handles data input, validation, storage, and display. The use of separate files for validation and database logic demonstrates the adherence to object oriented programming, and shows that I can keep program designs modular and readable for easier maintenance and collaboration. 

Working on this enhancement helped me better understand how important good database functionality is in program development. I got more comfortable using SQLite, writing queries, and structuring data so it can be manipulated into useful visualizations. The biggest challenge I faced was getting the CSV upload to function properly, as well as the duplication skip for preexisting policies. I had to make sure the file was read correctly, that the data matched the expected format, and that duplicate policy numbers were skipped without breaking the database. Getting that logic to work cleanly alongside the rest of the app took a lot of trial and error. I also had to make sure invalid inputs never made it into the database, which meant tightening up validation and making sure errors were shown clearly to the user instead of crashing the app or generating callback errors on Dash.

<p><strong>References</strong></p>
<ul>
  <li>
    <a href="https://www.geeksforgeeks.org/sqlite/sqlite-tutorial/" target="_blank">
      GeeksforGeeks. (2025, July 23). SQLite Tutorial
    </a>
  </li>
</ul>


