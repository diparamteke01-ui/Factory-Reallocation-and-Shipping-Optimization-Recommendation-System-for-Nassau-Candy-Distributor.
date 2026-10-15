# Factory Reallocation & Shipping Optimization Recommendation System

## Submission contents
- `app.py` — Streamlit prototype dashboard
- `Nassau Candy Distributor.csv` — source dataset
- `Research_Paper_Factory_Shipping_Optimization.docx` and `.pdf`
- `Executive_Summary_Factory_Shipping_Optimization.docx` and `.pdf`
- `requirements.txt` — Python dependencies

## Run locally (Windows)
```bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -r requirements.txt
streamlit run app.py
```
Open the local URL printed in the terminal, usually http://localhost:8501.

## Important scientific limitation
The supplied CSV does not contain shipment-level factory assignment history, actual delivery dates, factory capacities, destination coordinates, or actual lane-level freight charges. The current dashboard uses the factory coordinates and product-to-factory mapping provided in the project brief plus illustrative distance-based transit and cost assumptions. It is a scenario demonstrator, not a trained prediction model and not evidence of realized savings. The order-to-ship date gap is unusually large (median 1,274 days) and must be validated before modeling.

## Recommended next data
Actual assigned factory, dispatch and delivery timestamps, destination postal/address coordinates, actual freight charges, factory capacity, product eligibility, inventory constraints, and service-level requirements.
