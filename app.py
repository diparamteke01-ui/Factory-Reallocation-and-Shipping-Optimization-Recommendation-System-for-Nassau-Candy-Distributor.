import math
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title='Nassau Factory & Shipping Optimizer', page_icon='🚚', layout='wide')

FACTORIES = pd.DataFrame([
    {"Factory": "Lot's O' Nuts", "Latitude": 32.881893, "Longitude": -111.768036},
    {"Factory": "Wicked Choccy's", "Latitude": 32.076176, "Longitude": -81.088371},
    {"Factory": "Sugar Shack", "Latitude": 48.119140, "Longitude": -96.181150},
    {"Factory": "Secret Factory", "Latitude": 41.446333, "Longitude": -90.565487},
    {"Factory": "The Other Factory", "Latitude": 35.117500, "Longitude": -89.971107},
])
PRODUCT_FACTORY = {
    'Wonka Bar - Nutty Crunch Surprise': "Lot's O' Nuts",
    'Wonka Bar - Fudge Mallows': "Lot's O' Nuts",
    'Wonka Bar -Scrumdiddlyumptious': "Lot's O' Nuts",
    'Wonka Bar - Milk Chocolate': "Wicked Choccy's",
    'Wonka Bar - Triple Dazzle Caramel': "Wicked Choccy's",
    'Laffy Taffy': 'Sugar Shack', 'SweeTARTS': 'Sugar Shack', 'Nerds': 'Sugar Shack',
    'Fun Dip': 'Sugar Shack', 'Fizzy Lifting Drinks': 'Sugar Shack',
    'Everlasting Gobstopper': 'Secret Factory', 'Hair Toffee': 'The Other Factory',
    'Lickable Wallpaper': 'Secret Factory', 'Wonka Gum': 'Secret Factory',
}
# Approximate destination coordinates by state. These are state-level proxies, not customer addresses.
STATE_CENTERS = {
'Alabama':(32.8067,-86.7911),'Arizona':(34.2744,-111.6602),'Arkansas':(34.8938,-92.4426),'California':(37.1841,-119.4696),
'Colorado':(38.9972,-105.5478),'Connecticut':(41.6219,-72.7273),'Delaware':(39.1453,-75.4189),'District of Columbia':(38.9072,-77.0369),
'Florida':(28.6305,-82.4497),'Georgia':(32.6415,-83.4426),'Idaho':(44.3509,-114.6130),'Illinois':(40.0417,-89.1965),
'Indiana':(39.8942,-86.2816),'Iowa':(42.0751,-93.4960),'Kansas':(38.4937,-98.3804),'Kentucky':(37.5347,-85.3021),
'Louisiana':(31.0689,-91.9968),'Maine':(45.3695,-69.2428),'Maryland':(39.0550,-76.7909),'Massachusetts':(42.2596,-71.8083),
'Michigan':(44.3467,-85.4102),'Minnesota':(46.2807,-94.3053),'Mississippi':(32.7364,-89.6678),'Missouri':(38.3566,-92.4580),
'Montana':(47.0527,-109.6333),'Nebraska':(41.5378,-99.7951),'Nevada':(39.3289,-116.6312),'New Hampshire':(43.6805,-71.5811),
'New Jersey':(40.1907,-74.6728),'New Mexico':(34.4071,-106.1126),'New York':(42.9538,-75.5268),'North Carolina':(35.5557,-79.3877),
'North Dakota':(47.4501,-100.4659),'Ohio':(40.2862,-82.7937),'Oklahoma':(35.5889,-97.4943),'Oregon':(43.9336,-120.5583),
'Pennsylvania':(40.8781,-77.7996),'Rhode Island':(41.6762,-71.5562),'South Carolina':(33.9169,-80.8964),'South Dakota':(44.4443,-100.2263),
'Tennessee':(35.8580,-86.3505),'Texas':(31.4757,-99.3312),'Utah':(39.3055,-111.6703),'Vermont':(44.0687,-72.6658),
'Virginia':(37.5215,-78.8537),'Washington':(47.3826,-120.4472),'West Virginia':(38.6409,-80.6227),'Wisconsin':(44.6243,-89.9941),
'Wyoming':(42.9957,-107.5512),'Alaska':(63.5888,-154.4931),'Hawaii':(19.8968,-155.5828)
}
MODE_SPEED_KMPD = {'Same Day': 700, 'First Class': 600, 'Second Class': 450, 'Standard Class': 350}
MODE_COST_PER_KM = {'Same Day': 0.18, 'First Class': 0.12, 'Second Class': 0.08, 'Standard Class': 0.05}
HANDLING_DAYS = 1.0

@st.cache_data
def load_data(uploaded):
    if uploaded is not None:
        df = pd.read_csv(uploaded)
    else:
        p = Path(__file__).with_name('Nassau Candy Distributor.csv')
        df = pd.read_csv(p)
    for c in ['Sales','Units','Gross Profit','Cost']:
        if c in df: df[c] = pd.to_numeric(df[c], errors='coerce')
    for c in ['Order Date','Ship Date']:
        if c in df: df[c] = pd.to_datetime(df[c], errors='coerce', dayfirst=True)
    return df

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(min(1, math.sqrt(a)))

def scenario_table(product, state, ship_mode, speed_weight, product_summary):
    dest = STATE_CENTERS.get(state)
    if dest is None:
        dest = (39.8283, -98.5795)  # transparent fallback: approximate contiguous-US center
        location_note = 'Destination state is not mapped; distance uses an approximate US-center fallback.'
    else:
        location_note = f'Destination uses the approximate geographic center of {state}.'
    current = PRODUCT_FACTORY.get(product)
    prod = product_summary[product_summary['Product Name'].eq(product)]
    gp = float(prod['Gross Profit'].iloc[0]) if not prod.empty else 0.0
    sales = float(prod['Sales'].iloc[0]) if not prod.empty else 0.0
    rows=[]
    for _, f in FACTORIES.iterrows():
        dist = haversine_km(f['Latitude'], f['Longitude'], dest[0], dest[1])
        days = HANDLING_DAYS + dist / MODE_SPEED_KMPD.get(ship_mode, 350)
        ship_cost = dist * MODE_COST_PER_KM.get(ship_mode, .05)
        # 0 = prioritize speed; 100 = prioritize estimated transport cost/profit protection.
        max_days = HANDLING_DAYS + 5500 / MODE_SPEED_KMPD.get(ship_mode, 350)
        max_cost = 5500 * MODE_COST_PER_KM.get(ship_mode, .05)
        speed_norm = days / max_days if max_days else 0
        cost_norm = ship_cost / max_cost if max_cost else 0
        score = (1-speed_weight/100)*speed_norm + (speed_weight/100)*cost_norm
        rows.append({'Factory':f['Factory'],'Distance (km, approx.)':dist,'Estimated transit days (proxy)':days,
                     'Estimated shipping cost (proxy $)':ship_cost,'Estimated profit after proxy shipping cost ($)':gp-ship_cost,
                     'Gross profit before shipping ($)':gp,'Sales ($)':sales,'Weighted objective score':score,
                     'Current assignment': f['Factory']==current})
    out=pd.DataFrame(rows).sort_values('Weighted objective score').reset_index(drop=True)
    out['Rank']=np.arange(1,len(out)+1)
    out['Recommendation'] = np.where(out['Current assignment'],'Current factory',np.where(out['Rank']==1,'Top alternative','Alternative'))
    return out, current, location_note

st.title('🚚 Factory Reallocation & Shipping Optimization')
st.caption('Nassau Candy Distributor | Scenario simulator and decision-support prototype')
st.warning('Prototype limitation: the supplied order dataset has no actual factory assignment history, shipping distance, or shipping-cost fields. Transit time and shipping cost below are illustrative distance-based proxies, not trained-model predictions or actual carrier quotes. Validate assumptions before operational use.')

with st.sidebar:
    st.header('Data & scenario controls')
    uploaded = st.file_uploader('Upload an updated CSV (optional)', type=['csv'])
    st.caption('Default data: Nassau Candy Distributor CSV bundled with this project.')
    speed_weight = st.slider('Optimization priority: speed ↔ profit protection', 0, 100, 50, help='0 = prioritize estimated transit time; 100 = prioritize proxy shipping cost / profit after proxy cost.')
    st.caption(f'Speed priority: {100-speed_weight}% · Profit/cost priority: {speed_weight}%')

df=load_data(uploaded)
required={'Product Name','Division','Region','State/Province','Ship Mode','Sales','Gross Profit','Cost'}
missing=required-set(df.columns)
if missing:
    st.error('The uploaded CSV is missing required columns: '+', '.join(sorted(missing)))
    st.stop()
product_summary=(df.groupby(['Product Name','Division'],dropna=False).agg(**{'Sales':('Sales','sum'),'Gross Profit':('Gross Profit','sum'),'Cost':('Cost','sum'),'Units':('Units','sum')}).reset_index())
product_summary['Gross Margin (%)']=np.where(product_summary['Sales']!=0,100*product_summary['Gross Profit']/product_summary['Sales'],np.nan)
product_summary=product_summary.sort_values('Gross Profit',ascending=False)

c1,c2,c3,c4=st.columns(4)
c1.metric('Products in dataset',f"{df['Product Name'].nunique():,}")
c2.metric('Total sales',f"${df['Sales'].sum():,.0f}")
c3.metric('Gross profit',f"${df['Gross Profit'].sum():,.0f}")
c4.metric('Weighted gross margin',f"{100*df['Gross Profit'].sum()/df['Sales'].sum():.1f}%" if df['Sales'].sum() else 'N/A')

st.sidebar.divider()
products=sorted(df['Product Name'].dropna().unique().tolist())
regions=sorted(df['Region'].dropna().astype(str).unique().tolist())
ship_modes=sorted(df['Ship Mode'].dropna().astype(str).unique().tolist())
selected_product=st.sidebar.selectbox('Product',products,index=0 if products else None)
selected_region=st.sidebar.selectbox('Region',regions)
selected_mode=st.sidebar.selectbox('Ship mode',ship_modes,index=ship_modes.index('Standard Class') if 'Standard Class' in ship_modes else 0)

# Region filter is applied to commercial performance context; destination geography uses the selected state proxy.
filtered=df[df['Region'].astype(str).eq(selected_region)]
state_options=sorted(filtered['State/Province'].dropna().astype(str).unique().tolist())
if not state_options: state_options=sorted(df['State/Province'].dropna().astype(str).unique().tolist())
def_state='Texas' if 'Texas' in state_options else state_options[0]
selected_state=st.sidebar.selectbox('Destination state proxy',state_options,index=state_options.index(def_state))
scenario,current_factory,loc_note=scenario_table(selected_product,selected_state,selected_mode,speed_weight,product_summary)

# Tabs implement the requested modules.
t1,t2,t3,t4=st.tabs(['Factory Optimization Simulator','What-If Scenarios','Recommendations','Risk & Impact'])
with t1:
    st.subheader('Factory performance for the selected product')
    st.write(f'**Product:** {selected_product} · **Division:** {df.loc[df["Product Name"].eq(selected_product),"Division"].mode().iloc[0] if not df.loc[df["Product Name"].eq(selected_product),"Division"].mode().empty else "Unknown"}')
    st.info(loc_note + ' The product-to-factory mapping follows the configuration supplied for this project. Products without a mapped factory have no known current assignment.')
    if current_factory:
        st.write(f'**Configured current factory:** {current_factory}')
    else:
        st.warning('No current factory is configured for this product (Kazookles). The app can compare candidate factories, but cannot calculate a current-vs-new improvement until an assignment is provided.')
    left,right=st.columns(2)
    with left:
        fig=px.bar(scenario.sort_values('Estimated transit days (proxy)'),x='Factory',y='Estimated transit days (proxy)',color='Current assignment',title='Estimated transit days by factory (proxy)',hover_data=['Distance (km, approx.)'])
        st.plotly_chart(fig,use_container_width=True)
    with right:
        fig=px.bar(scenario.sort_values('Estimated shipping cost (proxy $)'),x='Factory',y='Estimated shipping cost (proxy $)',color='Current assignment',title='Estimated shipping cost by factory (proxy)',hover_data=['Estimated profit after proxy shipping cost ($)'])
        st.plotly_chart(fig,use_container_width=True)
    st.dataframe(scenario[['Rank','Factory','Current assignment','Distance (km, approx.)','Estimated transit days (proxy)','Estimated shipping cost (proxy $)','Estimated profit after proxy shipping cost ($)','Recommendation']],use_container_width=True,hide_index=True)
    st.download_button('Download factory comparison CSV',scenario.to_csv(index=False).encode('utf-8'),file_name='factory_scenario_comparison.csv',mime='text/csv')
with t2:
    st.subheader('Current assignment vs best alternative')
    if current_factory:
        current_row=scenario[scenario['Factory'].eq(current_factory)]
        best_alt=scenario[~scenario['Factory'].eq(current_factory)].sort_values('Weighted objective score').head(1)
        if not current_row.empty and not best_alt.empty:
            cur=current_row.iloc[0]; alt=best_alt.iloc[0]
            lead_reduction=100*(cur['Estimated transit days (proxy)']-alt['Estimated transit days (proxy)'])/cur['Estimated transit days (proxy)'] if cur['Estimated transit days (proxy)'] else 0
            cost_saving=cur['Estimated shipping cost (proxy $)']-alt['Estimated shipping cost (proxy $)']
            a,b,c=st.columns(3)
            a.metric('Estimated transit reduction',f'{lead_reduction:.1f}%',help='Distance-based proxy, not an observed result.')
            b.metric('Estimated proxy cost change',f'${cost_saving:,.2f}',help='Positive means lower proxy shipping cost; not an actual freight quote.')
            c.metric('Recommended alternative',str(alt['Factory']))
            comp=pd.DataFrame({'Metric':['Transit days (proxy)','Shipping cost (proxy $)'],'Current factory':[cur['Estimated transit days (proxy)'],cur['Estimated shipping cost (proxy $)']],'Recommended alternative':[alt['Estimated transit days (proxy)'],alt['Estimated shipping cost (proxy $)']]})
            fig=go.Figure()
            fig.add_trace(go.Bar(name='Current',x=comp['Metric'],y=comp['Current factory']))
            fig.add_trace(go.Bar(name='Alternative',x=comp['Metric'],y=comp['Recommended alternative']))
            fig.update_layout(barmode='group',title='Scenario comparison (units differ by metric)')
            st.plotly_chart(fig,use_container_width=True)
            st.caption('These are scenario estimates based on factory-to-state-center distance and assumed mode rates. They are not causal estimates of real-world savings.')
    else:
        st.warning('Add a current factory assignment for this product to calculate current-versus-recommended changes.')
    st.markdown('**Scenario assumptions**')
    st.write(f'- Ship mode: {selected_mode}; assumed speed: {MODE_SPEED_KMPD[selected_mode]} km/day.')
    st.write(f'- Assumed proxy transport rate: ${MODE_COST_PER_KM[selected_mode]:.2f} per km; handling: {HANDLING_DAYS:.1f} day(s).')
    st.write('- Destination uses an approximate state centroid, not the customer address.')
with t3:
    st.subheader('Ranked factory reassignment suggestions')
    st.write('Ranking combines normalized proxy transit time and proxy shipping cost according to the sidebar priority slider.')
    recs=scenario.copy()
    if current_factory: recs=recs[~recs['Factory'].eq(current_factory)]
    recs=recs.sort_values('Weighted objective score').head(3)
    if recs.empty:
        st.info('No alternative factories available.')
    else:
        for _,r in recs.iterrows():
            with st.container(border=True):
                st.markdown(f"**#{int(r['Rank'])} · {r['Factory']}**")
                st.write(f"Estimated transit: **{r['Estimated transit days (proxy)']:.1f} days** · Approx. distance: **{r['Distance (km, approx.)']:,.0f} km**")
                st.write(f"Proxy shipping cost: **${r['Estimated shipping cost (proxy $)']:,.2f}** · Proxy profit after shipping: **${r['Estimated profit after proxy shipping cost ($)']:,.2f}**")
                st.caption('Candidate only: validate factory capacity, product compatibility, inventory, service levels and actual freight costs before execution.')
with t4:
    st.subheader('Risk and business impact checks')
    prod_row=product_summary[product_summary['Product Name'].eq(selected_product)]
    if not prod_row.empty:
        p=prod_row.iloc[0]
        x,y,z=st.columns(3)
        x.metric('Product gross margin',f"{p['Gross Margin (%)']:.1f}%")
        y.metric('Product gross profit',f"${p['Gross Profit']:,.2f}")
        z.metric('Current factory mapping',current_factory or 'Not assigned')
        if p['Gross Margin (%)'] < 20:
            st.error('Margin alert: this product has a low gross margin in the supplied dataset. Do not assume a factory move will improve margin without actual freight and production-cost data.')
        elif p['Gross Margin (%)'] < 45:
            st.warning('Margin watch: evaluate the impact of any added logistics or handling cost.')
        else:
            st.success('Gross margin is above the prototype alert thresholds; this does not guarantee that a reassignment is profitable.')
    risks=[]
    if not current_factory: risks.append('Missing current factory mapping: no baseline improvement can be calculated.')
    if 'Ship Date' in df and 'Order Date' in df:
        lag=(df['Ship Date']-df['Order Date']).dt.days.dropna()
        if not lag.empty and lag.median()>365: risks.append(f"Date quality warning: median order-to-ship difference is {lag.median():.0f} days. Verify date formats and data definitions before training a predictive model.")
    risks += ['Factory capacity and product-factory compatibility are not provided; all alternate factories are treated as candidates for demonstration only.',
              'Shipping cost per km and transit speed are editable assumptions in code, not sourced operational facts.',
              'Profit-after-shipping uses gross profit minus proxy transport cost; actual profit impact needs real freight, labor, capacity and production costs.']
    for r in risks: st.warning(r)
    st.markdown('**Data readiness checklist**')
    checklist=pd.DataFrame({'Required for production':['Actual factory assigned to each shipment/product','Actual ship date / delivery date with validated definitions','Factory capacity and product compatibility','Actual lane-level freight cost or rate card','Destination coordinates or postal-code geocoding','Inventory / service-level constraints'], 'Available in supplied CSV':['No','Dates present but require validation','No','No','No (state only)','No']})
    st.dataframe(checklist,use_container_width=True,hide_index=True)

st.divider()
st.caption('Prototype for analytical exploration only. Recommendations are not operational instructions until data, assumptions, constraints and model performance are validated.')
