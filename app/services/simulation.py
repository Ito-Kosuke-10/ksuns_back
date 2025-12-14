"""Simulation service for simple simulation functionality."""
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simple_simulation import (
    FundsCommentCategory,
    SimpleSimulationAnswer,
    SimpleSimulationResult,
    SimpleSimulationSession,
    SimulationStatus,
)
from app.models.axis import PlanningAxis, AxisScore
from app.schemas.simulation import FinancialForecast, SimulationResultResponse, SubmitSimulationRequest


# Required fields for store profile
REQUIRED_FIELDS = ["main_genre", "sub_genre", "seats", "price_point", "business_hours", "location"]

# ========================================
# ラベルマッピング定義
# ========================================

MAIN_GENRE_LABELS = {
    "izakaya": "居酒屋",
    "ramen": "ラーメン店",
    "cafe": "カフェ",
    "bar": "バー",
    "yakiniku": "焼肉店",
    "sushi": "寿司店",
    "italian": "イタリアン",
    "french": "フレンチ",
    "chinese": "中華料理店",
    "japanese": "和食店",
    "curry": "カレー店",
    "udon": "うどん店",
    "soba": "そば店",
    "takoyaki": "たこ焼き店",
    "okonomiyaki": "お好み焼き店",
    "gyudon": "牛丼店",
    "teishoku": "定食屋",
    "bakery": "ベーカリー",
    "sweets": "スイーツ店",
    "undecided_main": "飲食店",
}

SUB_GENRE_LABELS = {
    "izakaya_taishu": "大衆",
    "izakaya_modern": "モダン",
    "izakaya_standing": "立ち飲み",
    "ramen_tonkotsu": "豚骨系",
    "ramen_shoyu": "醤油系",
    "ramen_miso": "味噌系",
    "cafe_specialty": "スペシャルティコーヒー",
    "cafe_casual": "カジュアル",
    "bar_authentic": "本格派",
    "bar_casual": "カジュアル",
    "undecided_sub": "",
}

LOCATION_LABELS = {
    "near_station": "駅近",
    "shopping_street": "商店街",
    "office_area": "オフィス街",
    "residential": "住宅街",
    "tourist_area": "観光地",
    "roadside": "ロードサイド",
    "underground": "地下",
    "building_upper": "ビル上階",
}

TARGET_CUSTOMER_LABELS = {
    "near_station": "サラリーマン向け",
    "shopping_street": "地域密着型",
    "office_area": "ビジネスパーソン向け",
    "residential": "ファミリー向け",
    "tourist_area": "観光客向け",
    "roadside": "ドライバー向け",
    "underground": "通勤客向け",
    "building_upper": "隠れ家的",
}

# ========================================
# コンセプトサブコメント定義（業態×立地の一文コンセプト）
# ========================================

CONCEPT_SUB_COMMENTS = {
    "izakaya": {
        "near_station": "仕事帰りに寄れる、気軽な一杯の場",
        "shopping_street": "地元の常連が集う、温かな酒場",
        "office_area": "昼も夜も使える、頼れる一軒",
        "residential": "家族でも通える、身近な居酒屋",
        "tourist_area": "旅の思い出になる、和の酒場体験",
        "roadside": "車でも立ち寄れる、気軽な晩酌処",
        "underground": "雨でも安心、駅近の隠れ酒場",
        "building_upper": "知る人ぞ知る、落ち着く隠れ家",
        "default": "気軽に楽しめる、居心地の良い空間",
    },
    "ramen": {
        "near_station": "忙しい日でも満たす、駅前の一杯",
        "shopping_street": "街に根づく、通いたくなる一杯",
        "office_area": "ランチ需要を掴む、早く旨い一杯",
        "residential": "家族でも安心、日常に寄り添う味",
        "tourist_area": "遠方客にも刺さる、看板の一杯",
        "roadside": "車で寄れる、サッと満足の一杯",
        "underground": "雨の日も選ばれる、近場の一杯",
        "building_upper": "上階で味わう、こだわりの一杯",
        "default": "こだわりの一杯で、記憶に残る店へ",
    },
    "cafe": {
        "near_station": "通勤前後に寄れる、心ほどけるカフェ",
        "shopping_street": "買い物の合間に、ほっと一息の場所",
        "office_area": "仕事の合間に効く、短い休憩の拠点",
        "residential": "日常に溶け込む、近所の止まり木",
        "tourist_area": "旅の余韻を彩る、特別なカフェ時間",
        "roadside": "ドライブ途中に寄れる、休憩カフェ",
        "underground": "天候に左右されない、便利なカフェ",
        "building_upper": "上階で過ごす、静かなカフェ時間",
        "default": "くつろぎの時間を提供するカフェ空間",
    },
    "bar": {
        "near_station": "終電前に寄れる、気軽な一杯の場",
        "shopping_street": "街の夜に寄り添う、大人の止まり木",
        "office_area": "仕事終わりを整える、落ち着く一杯",
        "residential": "近所で楽しめる、静かな夜の居場所",
        "tourist_area": "旅の夜を彩る、特別なバー体験",
        "roadside": "車利用も想定し、軽食中心で提案",
        "underground": "隠れ感が映える、落ち着くバー空間",
        "building_upper": "上階の隠れ家で、特別な一杯を",
        "default": "会話と一杯を楽しむ、落ち着く空間",
    },
    "yakiniku": {
        "near_station": "駅前で集まれる、満足度高い焼肉",
        "shopping_street": "家族でも通える、街の焼肉店",
        "office_area": "仕事帰り需要を掴む、焼肉の定番店",
        "residential": "週末に選ばれる、家族向け焼肉体験",
        "tourist_area": "名物で惹きつける、焼肉の思い出",
        "roadside": "車で来やすい、広め席の焼肉店",
        "underground": "煙対策で安心、便利な焼肉店",
        "building_upper": "隠れ家感で選ばれる、上階焼肉店",
        "default": "特別感のある焼肉体験を提供します",
    },
    "sushi": {
        "near_station": "駅前で気軽に、上質な寿司体験",
        "shopping_street": "街に根づく、通える寿司の一軒",
        "office_area": "接待にも対応、安心の寿司品質",
        "residential": "家族の節目に選ばれる寿司時間",
        "tourist_area": "旅の一食を彩る、日本の寿司体験",
        "roadside": "車で来やすい、家族向け寿司店",
        "underground": "雨でも寄れる、便利な寿司の一軒",
        "building_upper": "上階で静かに味わう、寿司の隠れ家",
        "default": "丁寧な一貫で満足を届ける寿司店",
    },
    "italian": {
        "near_station": "駅近で気軽に、イタリアンのご褒美",
        "shopping_street": "街の普段使いになる、イタリアン",
        "office_area": "ランチも強い、使い勝手の良い店",
        "residential": "家族で楽しめる、温かなイタリアン",
        "tourist_area": "旅先で映える、特別な一皿体験",
        "roadside": "車で来店しやすい、ゆったりイタリアン",
        "underground": "天候に左右されない、便利な一軒",
        "building_upper": "上階の隠れ家で、ゆっくり食事を",
        "default": "気軽さと特別感を両立するイタリアン",
    },
    "french": {
        "near_station": "駅近で叶う、少し特別なフレンチ",
        "shopping_street": "街で楽しむ、肩ひじ張らないフレンチ",
        "office_area": "会食にも使える、上質なフレンチ",
        "residential": "記念日に選ばれる、落ち着くフレンチ",
        "tourist_area": "旅の夜を彩る、特別なコース体験",
        "roadside": "車で通える、ゆったりフレンチ時間",
        "underground": "隠れ感で映える、落ち着くフレンチ",
        "building_upper": "上階の隠れ家で、静かなコースを",
        "default": "上質な時間を届ける、フレンチの一軒",
    },
    "chinese": {
        "near_station": "駅前で頼れる、満足感ある中華",
        "shopping_street": "街の食卓になる、通える中華店",
        "office_area": "ランチ回転で勝つ、定番中華",
        "residential": "家族で楽しめる、やさしい中華",
        "tourist_area": "名物で惹きつける、旅の中華体験",
        "roadside": "車で来やすい、ボリューム中華店",
        "underground": "雨でも寄れる、便利な中華の一軒",
        "building_upper": "上階で落ち着く、隠れ中華の店",
        "default": "日常に馴染む、満足度の高い中華店",
    },
    "japanese": {
        "near_station": "駅近で味わう、ほっとする和の食事",
        "shopping_street": "街に根づく、通える和食の一軒",
        "office_area": "昼も夜も対応、使いやすい和食店",
        "residential": "家族で通える、やさしい和の味",
        "tourist_area": "旅の記憶に残る、日本の和食体験",
        "roadside": "車でも安心、ゆったり和食の店",
        "underground": "天候に左右されない、便利な和食店",
        "building_upper": "上階の隠れ家で、静かな和食時間",
        "default": "季節を感じる、丁寧な和食を届けます",
    },
    "curry": {
        "near_station": "駅前でサッと満足、香り立つカレー",
        "shopping_street": "街で愛される、通いたくなるカレー",
        "office_area": "ランチ需要を掴む、回転型カレー店",
        "residential": "家族にも馴染む、日常のカレー店",
        "tourist_area": "名物で惹きつける、旅先カレー体験",
        "roadside": "車で寄れる、満足感あるカレー店",
        "underground": "雨でも寄れる、近場のカレー店",
        "building_upper": "上階で味わう、こだわりカレーの店",
        "default": "スパイスで記憶に残る、カレーの一皿",
    },
    "udon": {
        "near_station": "駅近で手軽に、ほっとするうどん",
        "shopping_street": "街に根づく、毎日でも通える一杯",
        "office_area": "ランチに強い、早い・旨い・軽い店",
        "residential": "家族で安心、日常のうどん店",
        "tourist_area": "地域色で魅せる、旅のうどん体験",
        "roadside": "車でも寄れる、広め席のうどん店",
        "underground": "天候に左右されない、便利な一杯",
        "building_upper": "上階で落ち着く、静かなうどん時間",
        "default": "やさしい出汁で、毎日に寄り添う店",
    },
    "soba": {
        "near_station": "駅近で粋に、すっと整うそば時間",
        "shopping_street": "街で通える、日常そばの一軒",
        "office_area": "昼需要に強い、軽快なそば店",
        "residential": "家族で楽しめる、やさしいそばの味",
        "tourist_area": "旅の一食に残る、地のそば体験",
        "roadside": "車で寄れる、ゆったりそばの店",
        "underground": "雨でも寄れる、便利なそばの一杯",
        "building_upper": "上階の隠れ家で、静かなそば時間",
        "default": "香りと喉ごしで選ばれる、そばの一軒",
    },
    "takoyaki": {
        "near_station": "駅前でつい買う、熱々たこ焼き",
        "shopping_street": "街歩きに合う、気軽なたこ焼き",
        "office_area": "小腹需要を掴む、テイクアウト強化",
        "residential": "近所で楽しむ、家族向けたこ焼き",
        "tourist_area": "名物で惹きつける、たこ焼き体験",
        "roadside": "車でも買いやすい、持ち帰り導線",
        "underground": "天候に強い、立ち寄りたこ焼き店",
        "building_upper": "上階で意外性、隠れたこ焼き店",
        "default": "つい買いたくなる、熱々の一品を",
    },
    "okonomiyaki": {
        "near_station": "駅近で楽しむ、香ばしい鉄板体験",
        "shopping_street": "街に根づく、鉄板の定番店",
        "office_area": "仕事帰り需要に強い、満足鉄板店",
        "residential": "家族で囲める、鉄板の楽しさを",
        "tourist_area": "旅の思い出になる、鉄板の名物体験",
        "roadside": "車で来やすい、広め席の鉄板店",
        "underground": "匂い対策で安心、便利な鉄板店",
        "building_upper": "上階の隠れ家で、鉄板をゆっくり",
        "default": "香ばしさで選ばれる、鉄板の一軒",
    },
    "gyudon": {
        "near_station": "駅前で早い、旨い、満たされる一杯",
        "shopping_street": "街の味方になる、手軽な牛丼店",
        "office_area": "昼回転で勝つ、スピード牛丼店",
        "residential": "近所で助かる、日常の牛丼店",
        "tourist_area": "日本らしさで魅せる、牛丼体験",
        "roadside": "車で寄れる、手早い食事の拠点",
        "underground": "雨でも寄れる、便利なクイック店",
        "building_upper": "上階で意外性、落ち着く牛丼店",
        "default": "手軽さと満足感で選ばれる牛丼店",
    },
    "teishoku": {
        "near_station": "駅近で整う、日替わり定食の安心感",
        "shopping_street": "街で通える、毎日の定食屋",
        "office_area": "昼需要に強い、回転型の定食店",
        "residential": "家族にも馴染む、やさしい定食",
        "tourist_area": "地域の味を届ける、定食体験",
        "roadside": "車で寄れる、しっかり食べる定食屋",
        "underground": "天候に左右されない、便利な定食店",
        "building_upper": "上階の隠れ家で、落ち着く定食時間",
        "default": "栄養と満足で選ばれる、定食の一軒",
    },
    "bakery": {
        "near_station": "通勤に寄り添う、焼きたてパンの店",
        "shopping_street": "街歩きに合う、つい買うパン屋",
        "office_area": "昼にも強い、軽食パンの拠点",
        "residential": "毎日通える、近所のパン屋さん",
        "tourist_area": "旅のお土産にもなる、パンの名物店",
        "roadside": "車で立ち寄れる、まとめ買いの店",
        "underground": "天候に強い、便利なベーカリー",
        "building_upper": "上階で意外性、隠れベーカリー",
        "default": "焼きたての香りで選ばれるベーカリー",
    },
    "sweets": {
        "near_station": "帰り道に嬉しい、手土産スイーツの店",
        "shopping_street": "街で話題になる、つい寄る甘味店",
        "office_area": "差し入れ需要に強い、スイーツ拠点",
        "residential": "近所のご褒美になる、甘い時間",
        "tourist_area": "旅の思い出になる、映える甘味体験",
        "roadside": "車でも買いやすい、手土産導線",
        "underground": "天候に左右されない、便利な甘味店",
        "building_upper": "上階の隠れ家で、特別な甘味時間",
        "default": "ひと口で幸せになる、スイーツの一軒",
    },
    "undecided_main": {
        "near_station": "駅近で刺さる\"強み\"を一つ決めよう",
        "shopping_street": "街に合う提供価値を一文にまとめよう",
        "office_area": "昼需要に合う業態候補を絞ろう",
        "residential": "近所の常連が通う理由を作ろう",
        "tourist_area": "名物一つで選ばれる軸を作ろう",
        "roadside": "車導線に合う提供形態を決めよう",
        "underground": "立地特性に合う強みを言語化しよう",
        "building_upper": "隠れ家なら\"目的来店\"の理由を作ろう",
        "default": "まずは\"誰に何を\"を一文で決めましょう",
    },
    "default": {
        "default": "お客様に喜ばれる店舗を目指します",
    },
}

# ========================================
# 開店にあたっての留意事項
# ========================================

OPENING_NOTES = {
    "near_station": """【立地について】
駅近物件は家賃が高めですが、集客力があります。競合店との差別化が重要です。

【営業時間】
通勤時間帯（朝・夕方）の集客を意識したオペレーションを検討してください。

【ターゲット】
サラリーマンやOLが主要ターゲットとなります。回転率を意識した席配置が効果的です。""",

    "shopping_street": """【立地について】
商店街は地域密着型の営業が求められます。常連客の獲得が成功の鍵です。

【営業時間】
商店街の営業時間に合わせた運営を検討してください。

【ターゲット】
地域住民との関係構築が重要です。イベントや季節メニューで話題作りを。""",

    "office_area": """【立地について】
オフィス街はランチ需要が高く、回転率重視の運営が求められます。

【営業時間】
平日ランチの効率化と、夜の宴会需要の両立がポイントです。

【ターゲット】
ビジネスパーソン向けのスピーディーなサービスを心がけてください。""",

    "residential": """【立地について】
住宅街は家族連れやシニア層が主要ターゲットとなります。

【営業時間】
土日祝日の集客が見込めます。平日の集客戦略も検討してください。

【ターゲット】
地域に根差した営業で、口コミでの評判が重要です。""",

    "tourist_area": """【立地について】
観光地は季節変動が大きいため、閑散期対策が必要です。

【営業時間】
観光客の動線を意識した営業時間の設定を検討してください。

【ターゲット】
SNS映えするメニューや内装で、口コミ拡散を狙いましょう。""",

    "default": """【立地について】
立地特性を分析し、ターゲット顧客を明確にしましょう。

【営業時間】
ターゲット層の生活リズムに合わせた営業時間を設定してください。

【ターゲット】
競合分析を行い、差別化ポイントを明確にしましょう。""",
}

# ========================================
# 業態別比率マップ（収支予想用）
# ========================================

FINANCIAL_RATIO_BY_GENRE = {
    "izakaya": {"cost": 32.0, "labor": 28.0, "profit": 10.0},
    "ramen": {"cost": 30.0, "labor": 25.0, "profit": 12.0},
    "cafe": {"cost": 35.0, "labor": 30.0, "profit": 10.0},
    "bar": {"cost": 25.0, "labor": 30.0, "profit": 15.0},
    "yakiniku": {"cost": 38.0, "labor": 25.0, "profit": 10.0},
    "sushi": {"cost": 35.0, "labor": 25.0, "profit": 12.0},
    "italian": {"cost": 33.0, "labor": 27.0, "profit": 10.0},
    "french": {"cost": 35.0, "labor": 30.0, "profit": 10.0},
    "chinese": {"cost": 32.0, "labor": 25.0, "profit": 10.0},
    "japanese": {"cost": 33.0, "labor": 27.0, "profit": 10.0},
    "curry": {"cost": 30.0, "labor": 25.0, "profit": 12.0},
    "udon": {"cost": 28.0, "labor": 24.0, "profit": 12.0},
    "soba": {"cost": 28.0, "labor": 24.0, "profit": 12.0},
    "takoyaki": {"cost": 28.0, "labor": 22.0, "profit": 15.0},
    "okonomiyaki": {"cost": 30.0, "labor": 25.0, "profit": 12.0},
    "gyudon": {"cost": 30.0, "labor": 25.0, "profit": 10.0},
    "teishoku": {"cost": 32.0, "labor": 27.0, "profit": 10.0},
    "bakery": {"cost": 28.0, "labor": 30.0, "profit": 10.0},
    "sweets": {"cost": 32.0, "labor": 28.0, "profit": 10.0},
    "undecided_main": {"cost": 32.0, "labor": 27.0, "profit": 10.0},
    "default": {"cost": 32.0, "labor": 27.0, "profit": 10.0},
}


def calculate_axis_scores(answers: dict) -> dict[str, float]:
    """Calculate axis scores from simulation answers."""
    scores = {
        "concept": 0.0,
        "funds": 0.0,
        "compliance": 0.0,
        "operation": 0.0,
        "location": 0.0,
        "interior": 0.0,
        "marketing": 0.0,
        "menu": 0.0,
    }

    main_genre = answers.get("main_genre", [])
    if main_genre and main_genre[0] != "undecided_main":
        scores["concept"] = 5.0

    sub_genre = answers.get("sub_genre", [])
    if sub_genre:
        scores["concept"] += 2.5

    seats = answers.get("seats", [])
    if seats:
        scores["operation"] = 5.0

    price_point = answers.get("price_point", [])
    if price_point:
        scores["funds"] = 5.0

    location = answers.get("location", [])
    if location:
        scores["location"] = 5.0

    if scores["compliance"] == 0.0:
        scores["compliance"] = 1.0

    return scores


def generate_concept_name(profile: dict) -> str:
    """Generate concept name from profile selections."""
    location_code = profile.get("location", "")
    main_genre_code = profile.get("main_genre", "")
    sub_genre_code = profile.get("sub_genre", "")

    # Get labels
    location_label = LOCATION_LABELS.get(location_code, "")
    target_label = TARGET_CUSTOMER_LABELS.get(location_code, "")
    main_genre_label = MAIN_GENRE_LABELS.get(main_genre_code, "飲食店")
    sub_genre_label = SUB_GENRE_LABELS.get(sub_genre_code, "")

    # Build concept name
    parts = []
    if location_label:
        parts.append(location_label)
    if target_label:
        parts.append(target_label)
    if sub_genre_label:
        parts.append(sub_genre_label)
    parts.append(main_genre_label)

    return "の".join(parts) if len(parts) > 1 else main_genre_label


def generate_concept_sub_comment(profile: dict) -> str:
    """Generate 20-30 character sub-comment for concept."""
    main_genre_code = profile.get("main_genre", "default")
    location_code = profile.get("location", "default")

    genre_comments = CONCEPT_SUB_COMMENTS.get(main_genre_code, CONCEPT_SUB_COMMENTS["default"])
    comment = genre_comments.get(location_code, genre_comments.get("default", "お客様に喜ばれる店舗を目指します"))

    return comment


def generate_opening_notes(profile: dict) -> str:
    """Generate opening notes based on location.

    Note: This function is deprecated and always returns empty string.
    The opening_notes field is kept for API compatibility.
    """
    return ""


def calculate_financial_forecast(profile: dict) -> tuple[FinancialForecast, FundsCommentCategory, str]:
    """Calculate detailed financial forecast based on business type structure."""
    seats = profile.get("seats", 0)
    price_point = profile.get("price_point", 0)
    main_genre = profile.get("main_genre", "default")

    if isinstance(seats, str):
        seats = int(seats) if seats.isdigit() else 20
    if isinstance(price_point, str):
        price_point = int(price_point) if price_point.isdigit() else 3000

    # 1. 想定月商（70%稼働率）
    monthly_sales = int(seats * price_point * 30 * 0.7)

    # 2. 業態別比率を取得
    ratios = FINANCIAL_RATIO_BY_GENRE.get(main_genre, FINANCIAL_RATIO_BY_GENRE["default"])
    cost_ratio = ratios["cost"]
    labor_cost_ratio = ratios["labor"]
    target_profit_ratio = ratios["profit"]

    # 3. その他経費率（固定）
    other_costs_ratio = 15.0

    # 4. 家賃上限率を計算
    max_rent_ratio = 100 - cost_ratio - labor_cost_ratio - other_costs_ratio - target_profit_ratio
    max_rent_ratio = max(0, max_rent_ratio)  # 0未満は0に丸める

    # 5. 家賃上限（目安）
    estimated_rent = int(monthly_sales * max_rent_ratio / 100)

    # 6. 利益率（計画値として表示）
    profit_ratio = target_profit_ratio

    # 7. 損益分岐売上
    fixed_costs = estimated_rent + (monthly_sales * other_costs_ratio / 100)
    variable_cost_ratio = (cost_ratio + labor_cost_ratio) / 100
    if variable_cost_ratio < 1:
        break_even_sales = int(fixed_costs / (1 - variable_cost_ratio))
    else:
        break_even_sales = 0

    # 資金計画コメント
    if profit_ratio >= 15:
        category = FundsCommentCategory.RELAXED
        text = "収支バランスが良好です。安定した経営が期待できます。"
    elif profit_ratio >= 5:
        category = FundsCommentCategory.TIGHT
        text = "収支は標準的です。コスト管理を意識した運営が必要です。"
    else:
        category = FundsCommentCategory.TIGHT
        text = "収支が厳しい可能性があります。価格設定や経費の見直しを検討してください。"

    forecast = FinancialForecast(
        monthly_sales=monthly_sales,
        estimated_rent=estimated_rent,
        cost_ratio=round(cost_ratio, 1),
        labor_cost_ratio=round(labor_cost_ratio, 1),
        profit_ratio=round(profit_ratio, 1),
        break_even_sales=break_even_sales,
        funds_comment_category=category.value,
        funds_comment_text=text,
    )

    return forecast, category, text


def _build_store_profile(answers: dict) -> dict:
    """Build store profile from answers."""
    profile = {}
    for key in REQUIRED_FIELDS:
        value = answers.get(key, [])
        if value:
            profile[key] = value[0] if isinstance(value, list) else value
    return profile


async def _get_axis_id_map(db: AsyncSession) -> dict[str, int]:
    """Get mapping of axis codes to axis IDs."""
    result = await db.execute(select(PlanningAxis))
    axes = result.scalars().all()
    return {axis.code: axis.id for axis in axes}


async def process_simulation_submission(
    db: AsyncSession,
    payload: SubmitSimulationRequest,
    user_id: Optional[int],
) -> SimulationResultResponse:
    """Process simulation submission and return results."""

    # Convert answers to dict
    answers_dict = {item.question_code: item.values for item in payload.answers}

    # Build store profile
    profile = _build_store_profile(answers_dict)

    # Calculate scores
    axis_scores = calculate_axis_scores(answers_dict)

    # Generate concept sub-comment (concept_name is deprecated, always empty)
    concept_name = ""
    concept_sub_comment = generate_concept_sub_comment(profile)

    # Calculate financial forecast
    financial_forecast, funds_category, funds_text = calculate_financial_forecast(profile)

    # Generate opening notes
    opening_notes = generate_opening_notes(profile)

    # Build response
    def build_response(session_id: int) -> SimulationResultResponse:
        return SimulationResultResponse(
            session_id=session_id,
            axis_scores=axis_scores,
            concept_name=concept_name,
            concept_sub_comment=concept_sub_comment,
            financial_forecast=financial_forecast,
            opening_notes=opening_notes,
            # 後方互換性フィールド
            funds_comment_category=funds_category.value,
            funds_comment_text=funds_text,
            store_story_text="",
            concept_title=MAIN_GENRE_LABELS.get(profile.get("main_genre", ""), ""),
            concept_detail=SUB_GENRE_LABELS.get(profile.get("sub_genre", ""), ""),
            funds_summary=funds_text,
            monthly_sales=financial_forecast.monthly_sales,
        )

    # If no user and no guest token, return without saving
    if user_id is None and not payload.guest_session_token:
        return build_response(0)

    # Guest without token - require token
    if user_id is None and payload.guest_session_token == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guest session token is required for saving results",
        )

    # Check if session with same guest_session_token already exists
    session_obj = None
    if payload.guest_session_token:
        result = await db.execute(
            select(SimpleSimulationSession).where(
                SimpleSimulationSession.guest_session_token == payload.guest_session_token
            )
        )
        session_obj = result.scalar_one_or_none()

    if session_obj:
        # Update existing session
        await db.execute(
            delete(SimpleSimulationAnswer).where(
                SimpleSimulationAnswer.session_id == session_obj.id
            )
        )
        await db.execute(
            delete(SimpleSimulationResult).where(
                SimpleSimulationResult.session_id == session_obj.id
            )
        )
        session_obj.status = SimulationStatus.COMPLETED
        session_obj.user_id = user_id
    else:
        # Create new session
        session_obj = SimpleSimulationSession(
            user_id=user_id,
            guest_session_token=payload.guest_session_token if not user_id else None,
            status=SimulationStatus.COMPLETED,
        )
        db.add(session_obj)
        await db.flush()

    # Save answers
    for item in payload.answers:
        answer = SimpleSimulationAnswer(
            session_id=session_obj.id,
            question_code=item.question_code,
            answer_values={"values": item.values},
        )
        db.add(answer)

    # Save result
    result_obj = SimpleSimulationResult(
        session_id=session_obj.id,
        axis_scores=axis_scores,
        funds_comment_category=funds_category,
        funds_comment_text=funds_text,
        store_story_text="",
    )
    db.add(result_obj)

    # If user is logged in, save axis scores
    if user_id:
        axis_map = await _get_axis_id_map(db)
        for axis_code, score in axis_scores.items():
            if axis_code in axis_map:
                axis_score = AxisScore(
                    user_id=user_id,
                    axis_id=axis_map[axis_code],
                    score=score,
                )
                db.add(axis_score)

    await db.commit()

    return build_response(session_obj.id)


async def attach_session_to_user(
    db: AsyncSession,
    session_id: int,
    user_id: int,
) -> Optional[SimulationResultResponse]:
    """Attach an existing simulation session to a user."""

    # Get session
    result = await db.execute(
        select(SimpleSimulationSession).where(SimpleSimulationSession.id == session_id)
    )
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        return None

    # Update user_id
    session_obj.user_id = user_id

    # Get simulation result
    result = await db.execute(
        select(SimpleSimulationResult).where(SimpleSimulationResult.session_id == session_id)
    )
    sim_result = result.scalar_one_or_none()

    if not sim_result:
        return None

    # Save axis scores for user
    axis_map = await _get_axis_id_map(db)
    for axis_code, score in sim_result.axis_scores.items():
        if axis_code in axis_map:
            axis_score = AxisScore(
                user_id=user_id,
                axis_id=axis_map[axis_code],
                score=score,
            )
            db.add(axis_score)

    await db.commit()

    # Build default financial forecast for attached sessions
    forecast = FinancialForecast(
        monthly_sales=None,
        estimated_rent=None,
        cost_ratio=None,
        labor_cost_ratio=None,
        profit_ratio=None,
        break_even_sales=None,
        funds_comment_category=sim_result.funds_comment_category.value,
        funds_comment_text=sim_result.funds_comment_text or "",
    )

    return SimulationResultResponse(
        session_id=session_id,
        axis_scores=sim_result.axis_scores,
        concept_name="",
        concept_sub_comment="",
        financial_forecast=forecast,
        opening_notes="",
        funds_comment_category=sim_result.funds_comment_category.value,
        funds_comment_text=sim_result.funds_comment_text or "",
        store_story_text=sim_result.store_story_text or "",
        concept_title="",
        concept_detail="",
        funds_summary=sim_result.funds_comment_text or "",
        monthly_sales=None,
    )
