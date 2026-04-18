---
layout: default
title: Home
---

# > tyler_

computer science capstone portfolio

---

## > professional_self_assessment

Write your self assessment here.

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

### enhancement_1 : software design and engineering

This artifact was selected for this enhancement due to its glaring security issues. Primarily, the original artifact contained hardcoded credentials for access, which was identified as a major security risk. The most important components of this artifact that showcase my skills are the authentication flow and the integration of multi factor authentication into the login process. This required restructuring how the application handles user sessions, adding a second verification step, and ensuring that users cannot access the dashboard without successfully completing both authentication steps. I also implemented basic role-based access control, which introduces different levels of permission within the application, namely, a read-only permission that will be unable to manipulate data in the case where a user just needs to visualize the data instead of manipulating it. Though the data privileges will be more apparent in the milestone 3 enhancement, this reflects how real systems restrict access based on user roles and responsibilities. Compared to the original version of the artifact, the enhanced version is significantly more secure and more aligned with modern software development standards. While the original application focused primarily on displaying data, the updated version introduces proper access control and authentication checks, making it more representative of a real-world professional system.
	In terms of course outcomes, this enhancement primarily supports outcome five, which focuses on developing a security mindset. By implementing MFA, I demonstrated an understanding of layered authentication and the importance of protecting systems from unauthorized access. I also worked toward outcome one through the role-based system, which allows different types of users to interact with the application in a controlled way. Outcome four is also partially demonstrated through the use of Python and Dash to implement a functional authentication system. No changes to my outcome coverage plan has been made. 
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
Description here.

### enhancement_3 : databases
Description here.


