# cas3140-grader
Grading client for the CAS3140 Quantum Computer Programming course.

To install:
```bash
pip install --upgrade git+https://github.com/ket-q/cas3140-grader.git
```

To use in your notebook:
```python
from cas3140_grader import submit, best_score, save_account, saved_account

save_account()  # This will ask for your token, and save the input as a file in your current Python environment

saved_account()  # This will return the location of your saved token. This token is needed to access the grading server.

result = submit(1, "sample_problem", myAnswer)  # Submit myAnswer to sample_problem inside lab 1
print(result.msg)  # See the grading feedback

best_score(1, "sample_problem")  # See what is your highest score achieved for sample_problem in lab 1
```