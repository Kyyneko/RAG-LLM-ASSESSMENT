# Sample Data for RAG-LLM Assessment Generator

This directory contains sample data for testing and demonstration purposes.

## 📁 Data Structure

```
data/
├── modules/                    # Learning modules (input for RAG)
│   ├── Algoritma dan Pemrograman/
│   └── Pemrograman Mobile/
└── assessments/               # Sample assessments (baseline comparison)
    ├── Algoritma dan Pemrograman/
    └── Pemrograman Mobile/
```

## 🎓 Available Subjects

### 1. Algoritma dan Pemrograman (Algorithms and Programming)

**Topics Covered:**
- Git & Github version control
- Python programming fundamentals
- Conditional statements and loops
- Functions, error handling, and regular expressions
- Object-Oriented Programming (OOP)
- Data types, collections, and operators

**Available Modules:**
- `Bab 1 Git & Github.pdf` - Version control with Git
- `Bab 3 Condition.pdf` - Conditional statements
- `Bab 4 Looping.pdf` - Looping constructs
- `BAB V. Function, Error Handling & RegEx.pdf` - Functions and error handling
- `BAB VI OOP_Pertemuan 1.docx` - OOP concepts part 1
- `BAB VI OOP_Pertemuan 2.pdf` - OOP concepts part 2
- `Data Types, Collection & Operator.pdf` - Python basics

**Sample Assessments:**
- `Tugas Praktikum 1 (Git & Github).pdf` - Git version control
- `Tugas Praktikum 2.pdf` - Programming fundamentals
- `Tugas praktikum 3.pdf` - Control structures
- `Tugas Praktikum 4.pdf` - Functions
- `Tugas Praktikum 5.pdf` - Advanced topics
- `Tugas Praktikum 6.pdf` - OOP implementation

### 2. Pemrograman Mobile (Mobile Programming)

**Topics Covered:**
- Android Activities and their lifecycle
- Android Intents for navigation
- RecyclerView for displaying lists
- UI components and layouts

**Available Modules:**
- `Bab 1 Activity.pdf` - Android Activities
- `Bab 2 Intent.pdf` - Android Intents
- `Bab 3 RecyclerView.pdf` - List management

**Sample Assessments:**
- `BAB 1.pdf` - Activity implementation
- `BAB 2.pdf` - Intent usage
- `BAB 4.pdf` - UI components
- `Bab 5.pdf` - Advanced Android topics

## 🔧 Usage Examples

### 1. Upload Module for Subject

```python
# Upload a module for Algoritma dan Pemrograman
files = {'file': open('data/modules/Algoritma dan Pemrograman/Bab 1 Git & Github.pdf', 'rb')}
data = {
    'subject_id': 1,
    'subject_name': 'Algoritma dan Pemrograman'
}

response = requests.post(
    'http://localhost:5000/api/rag/upload-module',
    files=files,
    data=data
)
```

### 2. Generate Assessment

```python
# Generate assessment for Git & Github topic
request_data = {
    'subject_id': 1,
    'subject_name': 'Algoritma dan Pemrograman',
    'topic': 'Git & Github Version Control',
    'class_name': 'Kelas A',
    'session_id': 1,
    'assistant_id': 1
}

response = requests.post(
    'http://localhost:5000/api/rag/generate',
    json=request_data
)
```

## 📊 Evaluation Data

The assessments in the `assessments/` directory serve as **baseline data** for comparing AI-generated assessments with human-created ones.

### Metrics for Comparison:

1. **Structural Completeness**
   - Presence of required tags (#SOAL, #REQUIREMENTS, #EXPECTED OUTPUT, #KUNCI JAWABAN)
   - Format compliance

2. **Content Quality**
   - Technical accuracy
   - Code examples presence
   - Requirements clarity

3. **Educational Value**
   - Learning objectives alignment
   - Difficulty level appropriateness
   - Practical relevance

## 🧪 Testing with Sample Data

### Running Evaluation Benchmark

```python
from evaluation import EndToEndEvaluator

evaluator = EndToEndEvaluator()

# Test with sample data
result = evaluator.run_benchmark(
    subjects=[1, 2],  # Both subjects
    samples_per_subject=3,
    output_file="evaluation_results.json"
)

print(f"Benchmark completed with {len(result)} evaluations")
```

### Compare AI vs Manual Assessments

```python
from evaluation.stats import ResearchReportGenerator

generator = ResearchReportGenerator()

# Compare AI-generated assessments with manual baseline
ai_scores = [85, 88, 82, 90, 87]  # AI-generated scores
manual_scores = [68, 70, 65, 72, 69]  # Manual assessment scores

report = generator.generate_comparison_report(
    group1_name="AI Generated",
    group1_scores=ai_scores,
    group2_name="Manual Baseline",
    group2_scores=manual_scores
)

print(f"Statistical comparison complete")
print(f"Mean difference: {report['practical_significance']['improvement_percentage']:.2f}%")
```

## 📈 Sample Size Considerations

For statistical significance in your skripsi research:

### Minimum Recommended Samples:
- **Per Subject**: 20-30 assessments
- **Total Evaluations**: 40-60 assessments
- **For Comparison Studies**: 30+ pairs of AI vs manual assessments

### Statistical Power:
- **Effect Size**: Medium (d = 0.5)
- **Power**: 80% (β = 0.2)
- **Alpha**: 0.05 (95% confidence)

## 🔍 Data Quality Notes

### Strengths:
✅ **Real Course Content**: Actual materials from university courses
✅ **Multiple Topics**: Diverse programming concepts covered
✅ **Both Input and Output**: Modules + assessments for full cycle testing
✅ **Indonesian Language**: Authentic educational content in target language

### Limitations:
⚠️ **Limited Subjects**: Only 2 subjects currently available
⚠️ **Small Sample Size**: ~10 assessments per subject
⚠️ **Single Institution**: Data from one university only
⚠️ **Time Period**: Limited to recent academic terms

## 🚀 Extending the Dataset

### Adding New Subjects:
1. Create subject directory: `data/modules/NewSubject/`
2. Add module PDFs/DOCX files
3. Create corresponding assessments directory
4. Update subject metadata in database

### Adding More Modules:
1. Place files in appropriate subject directory
2. Ensure consistent naming convention
3. Update file indexing in database

### Quality Guidelines:
- **File Format**: PDF or DOCX preferred
- **Language**: Indonesian for consistency
- **Content**: Complete educational modules
- **Structure**: Well-organized learning materials

## 📋 Data Usage Checklist

For research and testing:

- [ ] **Verify file integrity**: All files should be readable
- [ ] **Check content quality**: Modules should be complete and accurate
- [ ] **Maintain consistency**: Use consistent naming and structure
- [ ] **Document provenance**: Source and creation date information
- [ ] **Update regularly**: Add new modules and assessments as available
- [ ] **Backup data**: Keep copies of important datasets
- [ ] **Respect copyright**: Use only materials with proper permissions

## 🤝 Contributing Sample Data

To contribute additional sample data:

1. **Contact maintainers** for data contribution guidelines
2. **Ensure appropriate permissions** for educational content
3. **Follow naming conventions** for consistency
4. **Provide metadata** (subject, topic, difficulty level)
5. **Test with system** to ensure compatibility

---

**Note**: This sample data is provided for research and testing purposes only. Please respect copyright and educational use policies.