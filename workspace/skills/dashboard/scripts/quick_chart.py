#!/usr/bin/env python3
"""
Generate quick inline charts for chat responses.

Usage:
    python3 quick_chart.py --type bar --title "Ventas 2024" --labels "Q1,Q2,Q3,Q4" --values "100,150,120,180" --output /tmp/chart.png
    python3 quick_chart.py --type pie --title "Distribución" --labels "A,B,C" --values "30,50,20" --output /tmp/chart.png
    python3 quick_chart.py --type line --title "Tendencia" --labels "Ene,Feb,Mar" --values "10,20,15" --output /tmp/chart.png
"""

import argparse
import json
import sys

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    print("Error: matplotlib not installed. Run: pip install matplotlib")
    sys.exit(1)


def create_bar_chart(title, labels, values, output):
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['#2b6cb0', '#38a169', '#d69e2e', '#e53e3e', '#805ad5', '#dd6b20']
    bar_colors = [colors[i % len(colors)] for i in range(len(labels))]
    ax.bar(labels, values, color=bar_colors)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def create_pie_chart(title, labels, values, output):
    fig, ax = plt.subplots(figsize=(8, 8))
    colors = ['#2b6cb0', '#38a169', '#d69e2e', '#e53e3e', '#805ad5', '#dd6b20']
    chart_colors = [colors[i % len(colors)] for i in range(len(labels))]
    ax.pie(values, labels=labels, colors=chart_colors, autopct='%1.1f%%', startangle=90)
    ax.set_title(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def create_line_chart(title, labels, values, output):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(labels, values, marker='o', color='#2b6cb0', linewidth=2, markersize=8)
    ax.fill_between(range(len(values)), values, alpha=0.1, color='#2b6cb0')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


CHART_TYPES = {
    'bar': create_bar_chart,
    'pie': create_pie_chart,
    'line': create_line_chart,
}


def main():
    parser = argparse.ArgumentParser(description='Generate quick charts')
    parser.add_argument('--type', required=True, choices=CHART_TYPES.keys())
    parser.add_argument('--title', default='Chart')
    parser.add_argument('--labels', required=True, help='Comma-separated labels')
    parser.add_argument('--values', required=True, help='Comma-separated numeric values')
    parser.add_argument('--output', required=True, help='Output image path')

    args = parser.parse_args()

    labels = [l.strip() for l in args.labels.split(',')]
    values = [float(v.strip()) for v in args.values.split(',')]

    if len(labels) != len(values):
        print("Error: labels and values must have the same count")
        sys.exit(1)

    CHART_TYPES[args.type](args.title, labels, values, args.output)
    print(f"Chart saved: {args.output}")


if __name__ == "__main__":
    main()
