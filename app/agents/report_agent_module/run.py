#from template_generator import ResultTemplate, Product_recommendation, Secifications_Display, Secifications_Processor,Secifications_Storage, Secifications_Battery,Secifications_Design,Secifications_Color_Options, Secifications_Pencil_Support,Secifications_Charging_Port,Reviews_General_Users,Reviews_Youtuber,Purchase_Info_Stores
from .template_generator import ResultTemplate, Product, Reviews, Purchase_Info_Stores
import pprint

# product
generator = ResultTemplate()
item_product=Product()
item_product.show()
result_dict = generator.dict
reconmmendation=item_product.recommendation
reconmmendation.show()
reconmmendation.name="아이패드 에어 4세대"
reconmmendation.category="태블릿"
reconmmendation.main_reason="가격대비 성능이 우수"
reconmmendation.sub_reason="디자인이 예쁘고 성능이 좋음"
reconmmendation.good_person=["영상 감상을 좋아하는 사람","멀티태스킹을 자주 하는 사람"]
reconmmendation.bad_person=["저가형 태블릿을 찾는 사람","가격이 민감한 사람"]
reconmmendation.set_value(result_dict)

# specifications > display
display=item_product.display
display.show()
display.size="10.9인치"
display.resolution="2360 x 1640"
display.refresh_rate="60Hz"
display.description="고화질 영상 감상에 적합"
display.set_value(result_dict)

# specifications > processor
processor=item_product.processor
processor.show()
processor.model="Apple A14 Bionic"
processor.equivalent="아이폰 12 등급"
processor.description="일반적인 웹서핑 및 멀티태스킹에 충분"
processor.set_value(result_dict)

# specifications > storage
storage=item_product.storage
storage.show()
storage.options=["64GB"]
storage.expandable="128GB 옵션 없음"
storage.description="기본 사용에는 충분하지만 대용량 저장에는 한계"
storage.set_value(result_dict)

# specifications > battery
battery=item_product.battery
battery.show()
battery.capacity="최대 10시간 사용 가능"
battery.description="일반적인 사용에는 문제없음"
battery.set_value(result_dict)

# specifications > design
design=item_product.design
design.show()
design.features=["베젤 축소", "홈 버튼 제거", "지문 인식 탑재"]
design.description="깔끔하고 현대적인 디자인"
design.set_value(result_dict)

# specifications > color_options
color_options=item_product.color_options
color_options.show()
color_options.color_options=["블루", "핑크", "옐로우", "실버"]
color_options.set_value(result_dict)

# specifications > pencil_support
pencil_support=item_product.pencil_support
pencil_support.show()
pencil_support.supported="애플펜슬 1세대"
pencil_support.charging="번거로운 충전 방식 (별매)"
pencil_support.description="필기 및 그릴 작업에 적합"
pencil_support.set_value(result_dict)

# specifications > charging_port
charging_port=item_product.charging_port
charging_port.show()
charging_port.type="USB-C"
charging_port.limitation="라이트닝 미지원"
charging_port.description="기존 아이폰 충전기 사용 불가, 데이터 전송 속도 제한"
charging_port.set_value(result_dict)
item_review=Reviews()
item_review.show()
# reviews > youtuber
youtuber=item_review.youtuber
youtuber.show()
youtuber.name="UNDERkg"
youtuber.subscribers="78.8만 명"
youtuber.title="끊이지 않는 마진, 아이패드 (10세대) 리뷰"
youtuber.views="46만 회"
youtuber.time_since_upload="2년 전"
youtuber.timestamp1="0:31"
youtuber.timestamp2="2:46"
youtuber.timestamp3="4:16"
youtuber.timestamp4="6:01"
youtuber.timestamp5="7:31"
youtuber.timestamp6="9:01"
youtuber.timestamp1_description="디자인 및 외관 설명"
youtuber.timestamp2_description="디스플레이 특징 평가"
youtuber.timestamp3_description="프로세서 및 성능 테스트"
youtuber.timestamp4_description="배터리 수명 및 충전 포트 변경 사항"
youtuber.timestamp5_description="애플펜슬 호환성 평가"
youtuber.timestamp6_description="가격 및 총평"
youtuber.opinion="추천하지 않음"
youtuber.opinion_reason="디자인은 좋으나, 가격이 너무 올라감"
youtuber.pros=["새로운 디자인", "USB-C 도입"]
youtuber.cons=["애플펜슬 1세대 지원", "가격 상승"]
youtuber.link="https://www.youtube.com/watch?v=1"
youtuber.set_value(result_dict)

# reviews > general_users
general_users=item_review.general_users
general_users.show()
general_users.total_reviews=1363
general_users.positive_percentage="76%"
general_users.negative_percentage="24%"
general_users.positive_reviews=[
    "디자인 예뻐요",
    "영상 볼 때 최고",
    "배터리 오래가요",
    "USB-C 편리",
    "기본 성능 좋음"
]

general_users.negative_reviews=[
    "애플펜슬 문제",
    "가격 비쌈",
    "주사율 아쉬움",
    "포지션 애매"
]

general_users.user_comments=[
    {"user": "user1", "comment": "디자인은 예쁜데 가격이 너무 높아요."},
    {"user": "user2", "comment": "영상 볼 때 좋고 배터리도 오래가요."},
    {"user": "user3", "comment": "저장 공간이 부족해요."}
]
general_users.set_value(result_dict)
# purchase_info > stores
stores=Purchase_Info_Stores()
stores.show()
stores.site="쿠팡"
stores.option="블루, 64GB, Wi-Fi"
stores.price="508,880원"
stores.purchase_link="https://www.cupang.com/"
stores.rating=5.0
stores.set_value(result_dict)

pprint.pprint(result_dict, width=150)
#pprint.pprint(generator.dict_NONE)
