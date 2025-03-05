from konlpy.tag import Okt

def extract_keywords(text):
    okt = Okt()
    # stem=True 옵션으로 동사, 형용사 등을 기본형(어간)으로 변환
    tokens = okt.pos(text, stem=True)
    # 명사, 동사, 형용사 등 의미 있는 품사만 필터링 (원하는 품사는 필요에 따라 조정)
    keywords = [word for word, pos in tokens if pos in ('Noun', 'Verb', 'Adjective')]
    return keywords
sentence = '그림 연습용 아이패드 추천해주세요'
print(extract_keywords(sentence))
# 예시 문장
