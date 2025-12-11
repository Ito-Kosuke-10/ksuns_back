"""
深掘り機能の静的データ定義
軸コードをキーとした辞書形式で定義
"""

DEEP_DIVE_DATA = {
    "concept": [
        {
            "step": 1,
            "step_title": "導入と世界観",
            "cards": [
                {
                    "id": "concept_1_1",
                    "title": "動機・世界観",
                    "initial_question": "あなたがこのお店を通じて「どんな世界観」を実現したいですか？",
                },
                {
                    "id": "concept_1_2",
                    "title": "ターゲット",
                    "initial_question": "どんなお客様を「最も幸せにしたい」と考えていますか？",
                },
                {
                    "id": "concept_1_3",
                    "title": "コア価値",
                    "initial_question": "他店ではなく、お客様があなたのお店を選ぶ「決定的な理由」は何ですか？",
                },
                {
                    "id": "concept_1_4",
                    "title": "店舗タイプ",
                    "initial_question": "あなたのお店は「日常使い」ですか？それとも「ハレの日」利用ですか？",
                },
            ],
        },
        {
            "step": 2,
            "step_title": "具体化と差別化",
            "cards": [
                {
                    "id": "concept_2_1",
                    "title": "競合分析",
                    "initial_question": "想定ターゲットが利用している競合店を挙げてください。あなたの店が勝てるポイントはどこですか？",
                },
                {
                    "id": "concept_2_2",
                    "title": "提供体験",
                    "initial_question": "お客様がお店で過ごす時間の中で、「最も感動したり印象に残る体験」はどのようなものですか？",
                },
                {
                    "id": "concept_2_3",
                    "title": "店舗の個性",
                    "initial_question": "あなたのお店を「一言でいうとどんな場所」と表現できますか？",
                },
                {
                    "id": "concept_2_4",
                    "title": "顧客との関係性",
                    "initial_question": "常連になるための仕組みや仕掛けをどう作りますか？",
                },
            ],
        },
        {
            "step": 3,
            "step_title": "整合性と未来",
            "cards": [
                {
                    "id": "concept_3_1",
                    "title": "提供価値の整合性",
                    "initial_question": "設定した「ターゲット」と「提供するコア価値」は矛盾なく整合していますか？",
                },
                {
                    "id": "concept_3_2",
                    "title": "メッセージ",
                    "initial_question": "あなたの店を一言で表現する「キャッチフレーズ」を考えてください。",
                },
                {
                    "id": "concept_3_3",
                    "title": "未来への展望",
                    "initial_question": "このコンセプトが実現したとして、今後3～5年間でどんなブランドに成長させたいですか？",
                },
            ],
        },
    ],
    "financial": [],  # 他の軸は今後拡張
}
