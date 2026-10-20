# cas3140-grader
Grading client for the CAS3140 Quantum Computer Programming course.

## Installation:
```bash
pip install --upgrade git+https://github.com/ket-q/cas3140-grader.git
```

## Example usage
```python
from cas3140_grader import submit, best_score, save_account, saved_account, check_versions

check_versions()  # Optional: This will check if your Python and Qiskit installation matches the one on the grading server
# Grading will fail if they do not match

save_account()  # This will ask for your token, and save the input as a file in your current Python environment
# You only need to run the above command once per Python environment
saved_account()  # This will return the location of your saved token. This token is needed to access the grading server

result = submit("lab01", "sample_problem", myAnswer)  # Submit myAnswer to sample_problem inside lab 1
print(result.msg)  # See the grading feedback

best_score("lab01", "sample_problem")  # See what is your highest score achieved for sample_problem in lab 1

best_scores("lab01")  # See what are all your achieved scores for lab 1
```

## Troubleshooting
The following are common error messages you may encounter when running the notebook.

```bash
ConnectTimeout: A connection attempt failed because the connected party did not properly respond after a period of time
```
You are trying to connect to the grading server without a Yonsei campus IP address. If you are outside of campus,
please use YSVPN to connect to the server.

```bash
NameError: name 'FUNCTION_NAME' is not defined
```
The cas3140-grader is not imported into your project. You need to rerun the import command every time you
open the notebook.

```bash
RuntimeError: No submission token is available. Run save_account() once to save it for this Python environment, or pass token=... to this call.
```
Either you did not input a token, or the module was unable to find your saved token.

If you are on a new Python environment, you need to re-input your token.
To input your token, use ``save_function()``, which will ask for your token as input.

If you already input your token, the module may be unable to find your token.
Use ``saved_function()`` to see where the module thinks your token is.
It should say the location is found in ``account.json`` inside your current Python environment.
Please verify that the contents of ``account.json`` are correct.

If you are still unable to validate the token, you can instead pass the token manually
to each request to the grading server.
To do this, you can simply add ``token="YOUR_TOKEN_HERE"`` to each request.
For example, you can use ``submit("lab01", "problem01", my_answer, token="YOUR_TOKEN_HERE")``

```bash
The submission token is invalid or is no longer active. Check the token again.
```
This usually means the token you entered is incorrect.

To overwrite your saved token with the correct one, you need to run ``save_token(overwrite=True)``.
This will overwrite the saved token with your new input.