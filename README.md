# cas3140-grader
Grading client for the CAS3140 Quantum Computer Programming course.

To install:
```bash
pip install --upgrade git+https://github.com/ket-q/cas3140-grader.git
```

To use in your notebook:
```python
from cas3140_grader import submit, best_score
import getpass

TOKEN = getpass.getpass("Token: ")  # Your token is required to access the server

result = submit(1, 2, myAnswer, token=TOKEN)  # Submit myAnswer to lab 1 problem 2
print(result.msg)  # See the grading feedback

best_score(1, 2, token=TOKEN)  # See what is your highest score achieved for lab 1 problem 2
```