# BUSINESS SCIENCE UNIVERSITY
# AI DATA SCIENCE TEAM
# ***
# * Tools: Genomics Analysis Tools

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import warnings

warnings.filterwarnings("ignore")


def get_genomics_data_summary(
    data: pd.DataFrame,
    gene_column: str = "gene",
    mutation_column: str = "mutation_type",
    n_sample: int = 10,
) -> str:
    """
    Generate a summary of genomics/mutation data for LLM prompts.

    Parameters
    ----------
    data : pd.DataFrame
        The genomics dataset
    gene_column : str
        Name of the gene column
    mutation_column : str
        Name of the mutation type column
    n_sample : int
        Number of sample rows to include

    Returns
    -------
    str
        Formatted summary string
    """
    summary = []
    summary.append("# Genomics Data Summary")
    summary.append(f"Total variants/mutations: {len(data)}")

    # Check if columns exist
    if gene_column in data.columns:
        unique_genes = data[gene_column].nunique()
        top_genes = data[gene_column].value_counts().head(10)
        summary.append(f"\nGene Statistics:")
        summary.append(f"  - Unique genes affected: {unique_genes}")
        summary.append(f"\nMost frequently mutated genes:")
        for gene, count in top_genes.items():
            summary.append(f"  - {gene}: {count} mutations")
    else:
        summary.append(f"⚠️  Gene column '{gene_column}' not found!")

    # Mutation type summary
    if mutation_column in data.columns:
        mutation_types = data[mutation_column].value_counts()
        summary.append(f"\nMutation Type Distribution:")
        for mut_type, count in mutation_types.items():
            pct = (count / len(data) * 100) if len(data) > 0 else 0
            summary.append(f"  - {mut_type}: {count} ({pct:.1f}%)")

    # Chromosome distribution if available
    if "chromosome" in data.columns:
        chr_dist = data["chromosome"].value_counts().head(5)
        summary.append(f"\nTop 5 Chromosomes by mutation count:")
        for chr_name, count in chr_dist.items():
            summary.append(f"  - chr{chr_name}: {count}")

    # VAF (Variant Allele Frequency) if available
    if "vaf" in data.columns or "variant_allele_frequency" in data.columns:
        vaf_col = "vaf" if "vaf" in data.columns else "variant_allele_frequency"
        vaf_data = data[vaf_col].dropna()
        if len(vaf_data) > 0:
            summary.append(f"\nVariant Allele Frequency (VAF) Statistics:")
            summary.append(f"  - Mean VAF: {vaf_data.mean():.3f}")
            summary.append(f"  - Median VAF: {vaf_data.median():.3f}")
            summary.append(f"  - Min VAF: {vaf_data.min():.3f}")
            summary.append(f"  - Max VAF: {vaf_data.max():.3f}")

    # Sample data
    summary.append(f"\nSample Data (first {n_sample} rows):")
    sample_df = data.head(n_sample)
    summary.append(sample_df.to_string(max_cols=15, max_rows=n_sample))

    return "\n".join(summary)


def validate_genomics_data(
    data: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate genomics data structure.

    Parameters
    ----------
    data : pd.DataFrame
        The dataset to validate
    required_columns : List[str], optional
        List of required column names

    Returns
    -------
    Tuple[bool, List[str]]
        (is_valid, list_of_issues)
    """
    issues = []

    if data is None or data.empty:
        issues.append("Dataset is empty or None")
        return False, issues

    # Check required columns if specified
    if required_columns:
        for col in required_columns:
            if col not in data.columns:
                issues.append(f"Required column '{col}' not found")

    # Check for common genomics columns
    recommended_cols = ["gene", "chromosome", "position", "mutation_type"]
    missing_recommended = [col for col in recommended_cols if col not in data.columns]
    if missing_recommended:
        issues.append(
            f"Recommended columns missing: {', '.join(missing_recommended)}"
        )

    # Validate chromosome format if present
    if "chromosome" in data.columns:
        valid_chromosomes = set(
            [str(i) for i in range(1, 23)] + ["X", "Y", "M", "MT"]
        )
        invalid_chr = data["chromosome"].apply(
            lambda x: str(x).upper().replace("CHR", "")
        )
        invalid_chr = invalid_chr[~invalid_chr.isin(valid_chromosomes)]
        if len(invalid_chr) > 0:
            issues.append(
                f"Invalid chromosome values found: {invalid_chr.unique()[:5].tolist()}"
            )

    # Validate position if present
    if "position" in data.columns:
        if not pd.api.types.is_numeric_dtype(data["position"]):
            issues.append("Position column should be numeric")
        elif (data["position"] < 0).any():
            issues.append("Position column contains negative values")

    return len(issues) == 0, issues


def get_common_cancer_genes() -> List[str]:
    """
    Return list of commonly mutated cancer genes.

    Returns
    -------
    List[str]
        List of cancer driver genes
    """
    return [
        # Tumor suppressors
        "TP53",
        "PTEN",
        "RB1",
        "CDKN2A",
        "APC",
        "BRCA1",
        "BRCA2",
        "VHL",
        "NF1",
        "NF2",
        "STK11",
        "SMAD4",
        # Oncogenes
        "KRAS",
        "NRAS",
        "HRAS",
        "BRAF",
        "PIK3CA",
        "EGFR",
        "MYC",
        "ERBB2",
        "ALK",
        "RET",
        "MET",
        "KIT",
        # DNA repair
        "MLH1",
        "MSH2",
        "MSH6",
        "PMS2",
        "ATM",
        "BRIP1",
        "PALB2",
        # Epigenetic regulators
        "IDH1",
        "IDH2",
        "TET2",
        "DNMT3A",
        "ASXL1",
        "EZH2",
        # Cell cycle
        "CDK4",
        "CDK6",
        "CCND1",
        "CCNE1",
        # Other important
        "NOTCH1",
        "CTNNB1",
        "FBXW7",
        "SF3B1",
        "U2AF1",
    ]


def categorize_mutation_type(mutation: str) -> str:
    """
    Categorize mutation type into standard categories.

    Parameters
    ----------
    mutation : str
        Mutation description

    Returns
    -------
    str
        Standardized mutation category
    """
    mutation = str(mutation).upper()

    if any(
        x in mutation
        for x in ["MISSENSE", "SUBSTITUTION", "SNV", "SNP", "POINT_MUTATION"]
    ):
        return "Missense"
    elif any(x in mutation for x in ["NONSENSE", "STOP_GAINED"]):
        return "Nonsense"
    elif any(x in mutation for x in ["FRAMESHIFT", "INDEL", "INSERTION", "DELETION"]):
        return "Frameshift"
    elif any(x in mutation for x in ["SPLICE", "SPLICING"]):
        return "Splice_Site"
    elif any(x in mutation for x in ["SILENT", "SYNONYMOUS"]):
        return "Silent"
    elif any(x in mutation for x in ["INFRAME"]):
        return "Inframe"
    elif any(x in mutation for x in ["AMPLIFICATION", "CNV", "COPY_NUMBER"]):
        return "CNV"
    elif any(x in mutation for x in ["FUSION", "TRANSLOCATION"]):
        return "Fusion"
    else:
        return "Other"


def get_genomics_analysis_best_practices() -> str:
    """
    Return best practices for genomics analysis code generation.

    Returns
    -------
    str
        Best practices text
    """
    return """
# Genomics Analysis Best Practices:

1. **Data Preparation**:
   - Validate VCF format if loading variant files
   - Check for missing gene annotations
   - Standardize chromosome names (chr1 vs 1)
   - Filter low-quality variants (low coverage, low VAF)
   - Remove synonymous/silent mutations unless specifically requested

2. **Common Libraries**:
   - Use `import pandas as pd` for data manipulation
   - Use `import numpy as np` for numerical operations
   - Use `import plotly.graph_objects as go` for visualizations
   - For pathway analysis: can use simple gene set enrichment
   - For mutation signatures: consider trinucleotide context

3. **Mutation Analysis**:
   - Identify driver genes (TP53, KRAS, PIK3CA, etc.)
   - Calculate mutation burden (mutations per megabase)
   - Assess variant allele frequency (VAF) for clonality
   - Categorize mutations (missense, nonsense, frameshift, etc.)
   - Flag actionable/targetable mutations

4. **Gene-Level Analysis**:
   - Aggregate mutations by gene
   - Identify recurrently mutated genes
   - Consider gene length for mutation rate normalization
   - Annotate with cancer gene databases (COSMIC, OncoKB concepts)
   - Identify loss-of-function vs gain-of-function

5. **Pathway Analysis**:
   - Group genes by biological pathway (DNA repair, cell cycle, signaling)
   - Calculate pathway-level mutation burden
   - Identify enriched pathways
   - Consider pathway crosstalk

6. **Visualization**:
   - Oncoprint/heatmap for mutation matrix
   - Lollipop plots for protein domain mutations
   - Waterfall plots for mutation frequency
   - Rainfall plots for mutation distribution across genome
   - VAF histograms for clonality assessment

7. **Clinical Interpretation**:
   - Flag clinically actionable mutations
   - Identify resistance mutations
   - Consider tumor mutational burden (TMB) for immunotherapy
   - Check microsatellite instability (MSI) if applicable
   - Report druggable targets

8. **Error Handling**:
   - Handle missing gene annotations gracefully
   - Warn about low sample size
   - Validate chromosome/position ranges
   - Check for duplicate variants

9. **Output Format**:
   - Return structured dictionaries with clear keys
   - Include both summary statistics and detailed results
   - Provide gene-level and sample-level summaries
   - Make sure outputs are JSON-serializable
"""


def get_cancer_pathways() -> Dict[str, List[str]]:
    """
    Return dictionary of cancer-related pathways and their genes.

    Returns
    -------
    Dict[str, List[str]]
        Dictionary mapping pathway names to gene lists
    """
    return {
        "TP53_Pathway": [
            "TP53",
            "MDM2",
            "MDM4",
            "CDKN2A",
            "ATM",
            "CHEK2",
            "TP63",
            "TP73",
        ],
        "PI3K_AKT_mTOR": [
            "PIK3CA",
            "PIK3R1",
            "PTEN",
            "AKT1",
            "AKT2",
            "AKT3",
            "MTOR",
            "TSC1",
            "TSC2",
        ],
        "RAS_RAF_MEK_ERK": [
            "KRAS",
            "NRAS",
            "HRAS",
            "BRAF",
            "MAP2K1",
            "MAP2K2",
            "MAPK1",
            "NF1",
        ],
        "RTK_Signaling": ["EGFR", "ERBB2", "MET", "FGFR1", "FGFR2", "FGFR3", "KIT"],
        "WNT_Signaling": ["APC", "CTNNB1", "AXIN1", "AXIN2", "TCF7L2", "LRP5"],
        "NOTCH_Signaling": [
            "NOTCH1",
            "NOTCH2",
            "NOTCH3",
            "NOTCH4",
            "FBXW7",
            "MAML1",
        ],
        "Cell_Cycle": [
            "CDKN2A",
            "CDKN2B",
            "CDK4",
            "CDK6",
            "CCND1",
            "CCND2",
            "CCND3",
            "RB1",
        ],
        "DNA_Repair": [
            "BRCA1",
            "BRCA2",
            "ATM",
            "PALB2",
            "RAD51",
            "MLH1",
            "MSH2",
            "MSH6",
            "PMS2",
        ],
        "Chromatin_Modification": [
            "KMT2A",
            "KMT2C",
            "KMT2D",
            "ARID1A",
            "ARID1B",
            "SMARCA4",
            "PBRM1",
        ],
        "TGF_Beta": ["TGFBR1", "TGFBR2", "SMAD2", "SMAD3", "SMAD4"],
        "Apoptosis": ["BCL2", "BCL2L1", "BAX", "BAK1", "BID", "APAF1", "CASP3"],
    }


def calculate_tumor_mutation_burden(
    n_mutations: int, genome_size_mb: float = 30.0
) -> float:
    """
    Calculate tumor mutation burden (TMB).

    Parameters
    ----------
    n_mutations : int
        Number of somatic mutations
    genome_size_mb : float
        Size of sequenced genome in megabases (default 30 for typical exome)

    Returns
    -------
    float
        TMB in mutations per megabase
    """
    return n_mutations / genome_size_mb


def format_genomics_output(
    result: Any,
    analysis_type: str,
) -> Dict[str, Any]:
    """
    Format the output from a genomics analysis function.

    Parameters
    ----------
    result : Any
        The output from the genomics function
    analysis_type : str
        Type of analysis ('mutation_summary', 'pathway_enrichment', etc.)

    Returns
    -------
    Dict[str, Any]
        Formatted results
    """
    output = {
        "analysis_type": analysis_type,
        "success": True,
    }

    if isinstance(result, pd.DataFrame):
        output["data"] = result.to_dict()
        output["summary"] = (
            f"Generated {len(result)} rows of {analysis_type} results"
        )
    elif isinstance(result, dict):
        output.update(result)
    else:
        output["result"] = str(result)

    return output
