# Authors: Layolin Jesudhass & Isidro De Loera

# Imagen Product Recontextualization at Scale

This repository contains Jupyter notebooks and tools to perform large-scale product image recontextualization using Google's Gemini and Imagen Product Recontext models. It includes both the generation pipeline and an evaluation framework.

## Contents

### Notebooks

- **`imagen_product_recontext_at_scale.ipynb`**  
  Scales up product image recontextualization using Imagen. Handles:
  - Batch generation of recontextualized product images
  - Prompt engineering for diverse product contexts
  - Sequential and Prallel run as per the need

- **`evaluation_imagen_product_recontext.ipynb`**  
  Evaluates the generated images on various axes, such as:
    - Product Fidelity
    - Scene Realism
    - Aesthetic Quality
    - Brand Integrit
    - Policy Compliance
    - Imaging Quality
  - Sequential and Prallel run as per the need

## Getting Started

### Requirements

- Python 3.8+
- Jupyter or VSCode
- Google Cloud Vertex AI and  access to Imagen Product Recontext API
- Required Python libraries:
  - `numpy`
  - `pandas`
  - `matplotlib`
  - `PIL`
  - `transformers`
  - (Other dependencies depending on Imagen or evaluation model)

### Installation

git clone https://github.com/your-org/imagen-product-recontext

