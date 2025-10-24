import os
from flask import Flask, render_template, request
import deepl
from langdetect import detect, DetectorFactory

# langdetectのシードを固定し、一貫した検出結果を得る
DetectorFactory.seed = 0

app = Flask(__name__)

# 使用する言語コードを定義（表示用）
# ja, zh, vi に加え、en (英語) と ko (韓国語) を追加
TARGET_LANGUAGES = {
    'ja': '🇯🇵 日本語',
    'zh': '🇨🇳 中国語',
    'vi': '🇻🇳 ベトナム語',
    'en': '🇺🇸 英語',
    'ko': '🇰🇷 韓国語'
}

# DeepLが使うターゲット言語コードのマップ
# DeepLはターゲット言語として大文字のコードを使用
DEEPL_TARGETS = {
    'ja': 'JA',
    'zh': 'ZH',
    'vi': 'VI',
    # ★★★ 修正箇所: 'EN' を 'EN-US' に変更 ★★★
    'en': 'EN-US',
    'ko': 'KO'
}

# DeepL認証キーを環境変数から取得
DEEPL_AUTH_KEY = os.environ.get("DEEPL_AUTH_KEY")
translator = None
if DEEPL_AUTH_KEY:
    try:
        translator = deepl.Translator(DEEPL_AUTH_KEY)
        # 接続テストは初回アクセス時ではなく、translate_message内で行う
    except Exception as e:
        # キーが無効な場合はエラーメッセージとして表示される
        print(f"DeepL Translator Initialization Error: {e}")
        translator = None


# ==========================================================
# 翻訳ロジック関数
# ==========================================================
def translate_message(text, target_langs):
    """
    入力テキストの言語を自動検出し、選択されたターゲット言語に翻訳します。
    """
    global translator

    # DeepLクライアントが初期化されていない場合はエラーを返す
    if translator is None:
        return None, "エラー: DeepL API認証キーが正しく設定されていません。"

    # 1. 入力言語を検出
    try:
        detected_lang_base = detect(text)
    except:
        # 検出できなかった場合はデフォルトを日本語とする
        detected_lang_base = 'ja'

    # 2. 検出言語がDeepLのサポート外の場合はエラーを返す（可能性は低い）
    if detected_lang_base not in TARGET_LANGUAGES:
        return None, f"エラー: 検出された言語 ({detected_lang_base}) はサポートされていません。"

    translation_results = {}

    # 3. 各言語への翻訳を実行 (原文を含む)

    # 処理対象となる言語リストを決定:
    # 選択されたターゲット言語 + 検出言語 (原文表示のため)
    final_lang_codes = set(target_langs)

    # 検出言語が有効であれば、処理対象に含めます
    if detected_lang_base in TARGET_LANGUAGES:
        final_lang_codes.add(detected_lang_base)

    # ループの対象は、検出言語と選択されたターゲット言語すべて
    for target_code in final_lang_codes:
        # 検出言語は翻訳を行わず、原文を結果に含める
        if target_code == detected_lang_base:
            translation_results[target_code] = text
            continue

        # ターゲット言語コードを取得（DeepL用）
        deepl_target = DEEPL_TARGETS.get(target_code)

        if deepl_target:
            try:
                # DeepL翻訳を実行
                result = translator.translate_text(
                    text,
                    source_lang=DEEPL_TARGETS.get(detected_lang_base),
                    target_lang=deepl_target
                )
                translation_results[target_code] = result.text
            except deepl.exceptions.DeepLException as e:
                # DeepLのエラーをキャッチ
                return None, f"エラー: DeepL翻訳中に問題が発生しました - {e}"
            except Exception as e:
                # その他のエラーをキャッチ
                return None, f"エラー: 翻訳処理中に予期せぬエラーが発生しました - {e}"

    return translation_results, detected_lang_base


# ==========================================================
# Flask ルート関数
# ==========================================================
@app.route('/', methods=['GET', 'POST'])
def index():
    # ★★★ STEP 1: すべての変数を初期化 (UnboundLocalError対策) ★★★
    translation_results = None
    original_text = None
    detected_lang = None
    error_message = None
    full_output = ""
    # コピー用テキストの出力順を定義 (全言語)
    OUTPUT_ORDER = ['ja', 'zh', 'vi', 'en', 'ko']
    target_langs_selection = []  # テンプレートに渡すための選択された言語リスト

    if request.method == 'POST':
        input_text = request.form.get('input_text')

        # ★ STEP 2: 選択されたターゲット言語のリストを取得 ★
        target_langs = request.form.getlist('target_langs')
        target_langs_selection = target_langs  # テンプレートに渡すために保存

        # 翻訳ターゲットが一つも選択されていない場合はエラー
        if not target_langs:
            error_message = "エラー: 翻訳するターゲット言語が一つも選択されていません。"

        elif input_text and input_text.strip():
            # 翻訳関数に選択されたターゲット言語のリストを渡す
            # ★注意: translate_message関数の定義が2引数になっている必要があります
            translation_results, detected_lang = translate_message(input_text, target_langs)
            original_text = input_text

            if isinstance(detected_lang, str) and detected_lang.startswith("エラー:"):
                error_message = detected_lang
            elif translation_results:
                # ★ STEP 3: コピー用テキストを作成 (全言語を対象に、単一改行で結合) ★
                output_lines = []
                for lang_code in OUTPUT_ORDER:
                    if lang_code in translation_results:
                        lang_label = f"{TARGET_LANGUAGES[lang_code]}:"
                        # 原文はラベルを「(原文)」のように修正
                        if lang_code == detected_lang:
                            lang_label = f"{TARGET_LANGUAGES[lang_code]} (原文):"

                        output_lines.append(f"{lang_label}\n{translation_results[lang_code]}")

                # 改行（\n）で区切られた一つの文字列として保存 (空行を削除)
                full_output = "\n".join(output_lines)

    # HTMLテンプレート (templates/index.html) を表示する
    return render_template(
        'index.html',
        results=translation_results,
        original_text=original_text,
        all_langs=TARGET_LANGUAGES,  # 全言語をチェックボックス生成用に渡す
        detected_lang_code=detected_lang,
        error=error_message,
        full_output=full_output,
        # フォーム送信後もチェック状態を維持するために選択された言語リストを渡す
        selected_langs=target_langs_selection
    )


if __name__ == '__main__':
    # 開発環境で実行する場合
    app.run(debug=True)