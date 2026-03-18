# Frontend Design Skill

## Typography
- Use Inter or fitting Google Font, never system default
- Sizes: 14px body, 16px emphasis, 24-32px headings
- Line height: 1.5 body, 1.2 headings
- font-medium (500) for emphasis

## Color
- NEVER use #0000ff blue or #800080 purple
- 1 primary, 1 secondary, 1 accent color
- Grays: slate-50, slate-100, slate-800, slate-900
- Hover: darken 10%, same hue

## Spacing
- Scale: 4, 8, 12, 16, 24, 32, 48, 64
- Cards: p-6
- Between sections: gap-8 or gap-12
- Related items: gap-4
- No arbitrary values (p-7, gap-5)

## Layout
- Max width: 1280px (max-w-7xl)
- Grid for layouts, Flex for alignment
- Cards: shadow-sm or shadow-md
- Corners: rounded-lg cards, rounded-md buttons

## Don'ts
- No gradients unless requested
- No animations on everything
- No pure black - use slate-900
- No low-contrast text

## Streamlit Styling Example
```python
import streamlit as st

st.markdown("""
<style>
    .card {
        background: white;
        border-radius: 0.5rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        padding: 1.5rem;
    }
    .card h3 {
        font-size: 1.125rem;
        font-weight: 500;
        color: #0f172a;
    }
    .card p {
        margin-top: 0.5rem;
        font-size: 0.875rem;
        color: #475569;
    }
</style>
""", unsafe_allow_html=True)
```
