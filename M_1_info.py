import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import numpy as np
import plotly.express as px
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy import text as q_text
import configparser

def connection_db():
    """DB接続"""
    SQLALCHEMY_DATABASE_URL = "sqlite:///hoge.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    return engine

config = configparser.ConfigParser()
config.read("/Users/lambda/Python/config.ini", encoding='utf-8')

# config.ini ではなく st.secrets を使う
user = st.secrets["db_username"]
password = st.secrets["db_password"]
host = st.secrets["db_host"]
port = st.secrets["db_port"]
m1_db = st.secrets["db_name"]

m1_url = f'mysql+pymysql://{user}:{password}@{host}:{port}/{m1_db}?charset=utf8'
m1_engine = sa.create_engine(m1_url, echo=False)

# engine作成
m1_engine = sa.create_engine(m1_url, echo=False)

# --- 偏差値計算の関数 ---
def calculate_hensachi(x):
    # 標準偏差が0（全員同点など）の場合はエラーになるのを防ぐため、0なら偏差値50を返す
    if x.std() == 0:
        return 50
    return 50 + 10 * (x - x.mean()) / x.std()


m1_q = q_text(f"""
            SELECT
                f.performance_id,
                f.year, 
                f.performance_order,
                c.combi_name,
                c.agency,
                j.judge_name,
                s.score,
                f.round_stage
            FROM judge_scores s
            JOIN final_performances f USING(performance_id)
            JOIN combis c USING(combi_id)
            JOIN judges j USING(judge_id);
            """
        )

        
df = pd.read_sql(sql=m1_q, con=m1_engine.connect())
df["agency"] = df["agency"].str.replace("プロ（", "").str.replace("）", "")

def my_round(x, decimals=0):
    return np.floor(x * 10**decimals + 0.5) / 10**decimals


year_list = list(range(2001, 2011))+list(range(2015, 2026))
year_list.sort(reverse=True)

m1_score = pd.read_csv("data/得点/1st得点.csv")
m1_result = pd.read_csv("data/結果/決勝戦結果.csv")

st.set_page_config(layout='wide', page_title="M-1 Final Info", page_icon="")
st.title("M-1グランプリ 歴代1stラウンド得点")

cols = st.columns(5)
df_1st_round = df[df["round_stage"] == "1st"]
df_final_round = df[df["round_stage"] == "Final"]

agency_list = [
    "吉本興業", "松竹芸能", "プロダクション人力舎", "マセキ芸能社", "ケイダッシュステージ", "サンミュージックプロダクション", "ワタナベエンターテインメント",
    "グレープカンパニー", "タイタン", "SMA", "太田プロダクション", "M2カンパニー", "フラットファイヴ", "アマチュア", "ザ・森東", "ニチエンプロダクション", "アミー・パーク", 
    "吉本以外"
]

with cols[0]:
    year = st.selectbox(
        "開催年",
        ["通算"] + year_list,
        index=0
    )
if year == "通算":
    with cols[1]:
        group = st.selectbox(
            "",
            ["コンビ", "大会"],
            index=0
        )
    if group == "コンビ":
        with cols[2]:
            order = st.selectbox(
                "出番順",
                [i for i in range(1, 11)],
                index=None,
                placeholder="出番順"
            )
        with cols[3]:
            rank_1 = st.selectbox(
                "1stラウンド順位",
                [i for i in range(1, 11)]+["最下位"],
                index=None,
                placeholder="1stラウンド順位"
            )
        with cols[4]:
            agency = st.selectbox(
                "事務所",
                agency_list,
                index=None,
                placeholder="事務所"
            )

        df_1st_round = df_1st_round.groupby(["performance_id", "year", "performance_order", "combi_name", "agency"], as_index=False).agg(
            total_score = ("score", "sum"),
            avg_score=("score", "mean")
        )
        df_1st_round["順位"] = df_1st_round.groupby("year")["total_score"].rank(ascending=False, method="min")
        df_1st_round["total_score_7"] = df_1st_round["avg_score"]*7
        df_1st_round['hensachi'] = df_1st_round.groupby('year')['total_score'].transform(calculate_hensachi)
        df_1st_round["hensachi"] = my_round(df_1st_round["hensachi"], 2)
        df_1st_round["agency"] = df_1st_round["agency"].str.replace("プロ（", "").str.replace("）", "")
        df_1st_round = df_1st_round.rename(columns={
            "performance_order": "出番順", "combi_name": "コンビ名", "total_score": "得点", "avg_score": "得点率", 
            "total_score_7": "得点（7人換算）", "hensachi": "偏差値", "year": "年", "agency": "事務所"
            })
        if order:
            df_1st_round = df_1st_round[df_1st_round["出番順"] == order]
        if rank_1:
            if rank_1 == "最下位":
                df_1st_round = df_1st_round.sort_values("得点").groupby(["年"]).head(1).sort_values("performance_id")
            else:
                df_1st_round = df_1st_round[df_1st_round["順位"] == rank_1]
        if agency:
            if agency == "アマチュア":
                df_1st_round = df_1st_round[df_1st_round["事務所"] == "アマチュア"]
            elif agency == "吉本以外":
                df_1st_round = df_1st_round[~df_1st_round["事務所"].str.contains("吉本興業")]
            else:
                df_1st_round = df_1st_round[df_1st_round["事務所"].str.contains(agency)]


                
        df_1st_round = df_1st_round[["コンビ名", "事務所", "年", "出番順", "順位", "得点", "得点率", "得点（7人換算）", "偏差値"]]
        #df_1st_round = df_1st_round.reset_index(drop=True)
        
        styled_data = (
                df_1st_round.style
                .background_gradient(cmap="coolwarm", subset=["得点", "得点（7人換算）", "得点率"])
                .background_gradient(cmap="coolwarm", subset=["偏差値"], vmin=25, vmax=75)
                .format({
                    "順位": "{:.0f}",  # "合計得点"を整数表示に設定
                    "合計得点": "{:.0f}",  # "合計得点"を整数表示に設定
                    "得点率": "{:.2f}",    # "平均点"を小数点1桁に設定
                    "得点（7人換算）": "{:.1f}",     # "偏差値"を小数点1桁に設定
                    "偏差値": "{:.2f}",     # "偏差値"を小数点1桁に設定
                })
            )
        st.dataframe(styled_data, width="stretch")

else:
    with cols[1]:
        options = ["得点", "偏差値"]
        choice = st.selectbox(
            "表示項目",
            options,
            index=0,

        )
    df_1st_round = df_1st_round[df_1st_round["year"] == year]

    average_score = df_1st_round["score"].mean()

    df_1st_round["hensachi"] = df_1st_round[df_1st_round["round_stage"] == "1st"].groupby(["year", "judge_name"])['score'].transform(calculate_hensachi)
    df_score = df_1st_round.pivot(index='combi_name', columns='judge_name', values="score")
    df_hensachi = df_1st_round.pivot(index='combi_name', columns='judge_name', values="hensachi")
    df_score.index.name = "コンビ名"
    df_hensachi.index.name = "コンビ名"

    df_final_round = df_final_round[df_final_round["year"] == year]
    df_final_score = df_final_round.pivot(index='combi_name', columns='judge_name', values='score')
    df_final_score.index.name = "コンビ名"

    judges = list(df_1st_round["judge_name"].unique())

    df_1st = df_1st_round.groupby(["performance_id", "performance_order", "combi_name"], as_index=False).agg(
        Total=("score", "sum"),
        Average=("score", "mean")
    )
    df_final_score['Total'] = df_final_score.iloc[:, 0:len(judges)].sum(axis=1)
    df_final_round = df_final_round.groupby(["performance_id", "performance_order", "combi_name"], as_index=False).agg(
        total_score=("score", "sum")
    )

    combis = df_score.index
    final_combis = df_final_score.index

    df_score["combi_name"] = combis
    df_hensachi["combi_name"] = combis
    df_final_score["combi_name"] = final_combis
    df_score = pd.merge(df_score, df_1st, on=["combi_name"], how="left")
    df_hensachi = pd.merge(df_hensachi, df_1st, on=["combi_name"], how="left")
    df_final_score = pd.merge(df_final_score, df_final_round[["combi_name", "performance_order"]], on=["combi_name"], how="left")
    df_score = df_score.rename(columns={"Total": "合計得点", "Average": "得点率", "performance_order": "出番順", "combi_name": "コンビ名"})
    df_hensachi = df_hensachi.rename(columns={"Total": "合計得点", "Average": "得点率", "performance_order": "出番順", "combi_name": "コンビ名"})
    df_final_score = df_final_score.rename(columns={"Total": "各得票数", "performance_order": "出番順", "combi_name": "コンビ名"})
    #df_score = df_score.reset_index(drop=True)
    df_score["偏差値"] = df_score["合計得点"].transform(calculate_hensachi)
    df_hensachi["偏差値"] = df_hensachi["合計得点"].transform(calculate_hensachi)
    df_score["順位"] = df_score["合計得点"].rank(ascending=False, method="min")
    df_hensachi["順位"] = df_hensachi["合計得点"].rank(ascending=False, method="min")
    df_final_score["順位"] = df_final_score["各得票数"].rank(ascending=False, method="min")
    df_score = df_score[["コンビ名", "出番順", "順位", "合計得点", "得点率", "偏差値"] + judges]
    df_hensachi = df_hensachi[["コンビ名", "出番順", "順位", "合計得点", "得点率", "偏差値"] + judges]
    df_final_score = df_final_score[["コンビ名", "出番順", "順位", "各得票数"] + judges]
    #df_score.index = combis
    #df_hensachi.index = combis
    #df_final_score.index = final_combis
    #df_score.index.name = "コンビ名"
    #df_hensachi.index.name = "コンビ名"
    #df_final_score.index.name = "コンビ名"
    df_score = df_score.sort_values("出番順").reset_index(drop=True)
    df_hensachi = df_hensachi.sort_values("出番順").reset_index(drop=True)
    df_final_score = df_final_score.sort_values("出番順").reset_index(drop=True)

    hensachi_style_dict = {
                "順位": "{:.0f}",  # "合計得点"を整数表示に設定
                "合計得点": "{:.0f}",  # "合計得点"を整数表示に設定
                "得点率": "{:.2f}",    # "平均点"を小数点1桁に設定
                "得点（7人換算）": "{:.1f}",     # "偏差値"を小数点1桁に設定
                "偏差値": "{:.2f}",     # "偏差値"を小数点1桁に設定
            }
    score_style_dict = {
                "順位": "{:.0f}",  # "合計得点"を整数表示に設定
                "合計得点": "{:.0f}",  # "合計得点"を整数表示に設定
                "得点率": "{:.2f}",    # "平均点"を小数点1桁に設定
                "得点（7人換算）": "{:.1f}",     # "偏差値"を小数点1桁に設定
                "偏差値": "{:.2f}",     # "偏差値"を小数点1桁に設定
            }
    hensachi_style_dict.update({k: "{:.2f}" for k in judges})
    score_style_dict.update({k: "{:.0f}" for k in judges})

    styled_score = (
            df_score.style
            .background_gradient(cmap="coolwarm", subset=["合計得点", "得点率"]+judges)
            .background_gradient(cmap="coolwarm", subset=["偏差値"], vmin=25, vmax=75)
            .format(score_style_dict)
        )
    
    styled_hensachi = (
            df_hensachi.style
            .background_gradient(cmap="coolwarm", subset=["合計得点", "得点率"])
            .background_gradient(cmap="coolwarm", subset=["偏差値"]+judges, vmin=25, vmax=75)
            .format(hensachi_style_dict)
        )
    styled_final_data = (
            df_final_score.style
            .format({
                "順位": "{:.0f}",  # "合計得点"を整数表示に設定
            })
        )
    if choice == "得点":
        st.dataframe(styled_score, width="stretch")
    else:
        st.dataframe(styled_hensachi, width="stretch")

    st.write(f"平均点：{my_round(average_score, 1)}点")

    box_chart = px.box(df_1st_round, y = "score", x = "judge_name", color="judge_name", 
                       points="all",
                       hover_data=["combi_name"],
                       labels={
                            "score": "得点",
                            "judge_name": "審査員",
                            "combi_name": "コンビ名"
                        },
                        title = "得点分布"
                        )
    st.plotly_chart(box_chart)
    st.header("最終決戦 得票数")
    st.dataframe(styled_final_data, width="stretch")

