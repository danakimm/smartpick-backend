from app.agents.report_agent_module.utility_report import Node
import re
from .dummy import get_test_dummy
from .template_generator import ResultTemplate, Product, Reviews, Purchase_Info_Stores
from .bsae_reporter import BaseReporter
test_set = {'제품명':'APPLE 2024 iPad mini A17 Pro 7세대', 
    '가격': 749000, 
        '추천 이유': {'pros': ['장점 1', '장점 2', '장점 3'], 'cons': ['단점 1', '단점 2', '단점 3']}, 
            '핵심 사항': [{'항목': 'AI', '사양': '요약편집교정, 이미지 생성편집, 음성비서', '설명': '다양한 AI 기능으로 작업을 효율적으로 지원합니다.'}, 
                    {'항목': '규격', ' 사양': '가로: 134.8mm, 세로: 195.4mm, 두께: 6.3mm, 무게: 293g, 출시가: 749,000원', '설명': '작고 가벼운 디자인으로 휴대성이 뛰어납니다.'}, 
                    {'항목': '네트워크', '사양': 'Wi-Fi전용, 802.11ax(Wi-Fi 6E), 듀얼밴드, 블루투스v5.3', '설명': '최신 Wi-Fi 기술로 빠르고 안정적인 연결을 제공합니다.'}, 
                    {'항목': '배터리', '사양': '충전단자: C타입, USB3.0, 약 5,078mAh(19.3WH), 최대충전: 약20W', '설명': '오랜 사용 시간을 제공하며 빠른 충전이 가 능합니다.'}, 
                    {'항목': '벤치마크', '사양': 'AP싱글코어: 2953, AP멀티코어: 7441', '설명': '우수한 성능으로 다 양한 작업을 원활하게 처리합니다.'}, 
                    {'항목': '사운드', '사양': '스피커: 2개, 마이크: 2개', '설명': '양질의  오디오 경험을 제공합니다.'}, 
                    {'항목': '시스템', '사양': 'A17 Pro, 6코어, 램: 8GB, 용량: 128GB, microSD미지원', '설명': '최신 A17 Pro 칩으로 뛰어난 성능을 자랑합니다.'}, 
                    {'항목': '카메라', '사양': '후면: 1,200만화소, 전면: 1,200만화소, 4K@60fps, F1.8, 센터 스테이지, 슬로모션 동영상', '설명': '고화질 사진과 동영상 촬영이 가 능합니다.'
                }
        ]
}
flat_dict = {
    "recommendation.name": "아이패드 에어 4세대",
    "recommendation.category": "태블릿",
    "recommendation.main_reason": "가격대비 성능이 우수",
    "recommendation.sub_reason": "디자인이 예쁘고 성능이 좋음",
    "recommendation.good_person": ["영상 감상을 좋아하는 사람", "멀티태스킹을 자주 하는 사람"],
    "recommendation.bad_person": ["저가형 태블릿을 찾는 사람", "가격이 민감한 사람"],
    "display.size": "10.9인치",
    "display.resolution": "2360 x 1640",
    "display.refresh_rate": "60Hz",
    "display.description": "고화질 영상 감상에 적합",
    "processor.model": "Apple A14 Bionic",
    "processor.equivalent": "아이폰 12 등급",
    "processor.description": "일반적인 웹서핑 및 멀티태스킹에 충분",
    "storage.options": ["64GB"],
    "storage.expandable": "128GB 옵션 없음",
    "storage.description": "기본 사용에는 충분하지만 대용량 저장에는 한계",
    "battery.capacity": "최대 10시간 사용 가능",
    "battery.description": "일반적인 사용에는 문제없음",
    "design.features": ["베젤 축소", "홈 버튼 제거", "지문 인식 탑재"],
    "design.description": "깔끔하고 현대적인 디자인",
    "color_options.color_options": ["블루", "핑크", "옐로우", "실버"],
    "pencil_support.supported": "애플펜슬 1세대",
    "pencil_support.charging": "번거로운 충전 방식 (별매)",
    "pencil_support.description": "필기 및 그릴 작업에 적합",
    "charging_port.type": "USB-C",
    "charging_port.limitation": "라이트닝 미지원",
    "charging_port.description": "기존 아이폰 충전기 사용 불가, 데이터 전송 속도 제한"
}
class SpecificationReporter(BaseReporter):
    def __init__(self,input,query):
        script=[]
        script.append('현재 첫번째 시도입니다.')
        script.append('두번째 시도입니다. 다음 질문과 함꼐 다시 생각해 보세요,')
        script.append('세번째 시도입니다. 이전의 질의 응답과 함꼐 다시 생각해 보세요,')
        script.append('이번이 마지막 시도입니다. 이전의 질의 응답과 함꼐 다시 생각해 보세요, 이번엔 질문을 반환하지 않고 나머지 값을 최대한 채워서 반환합니다. 단 채울 값이 없다고 해서 관런없는 예시의 값을 채워서는 안됩니다. 정보가 없다면 관련 정보 없음으로 채우십시오, 자료에서 확인되지 않은 사실 또한 써서는 안됩니다.')
        require_key=["display.size","display.resolution","display.refresh_rate","display.description","processor.model","processor.equivalent","processor.description","storage.options","storage.expandable","storage.description","battery.capacity","battery.description","design.features","design.description","color_options.color_options","pencil_support.supported","pencil_support.charging","pencil_support.description","charging_port.type","charging_port.limitation","charging_port.description","recommendation.name","recommendation.category","recommendation.main_reason","recommendation.sub_reason","recommendation.good_person","recommendation.bad_person","site","option","price","purchase_link","rating"]
        table_content="""
                    ## 📌 Product 클래스

                    | 입력 변수명 | 설명 | 입력 예시 |
                    |------------|------|----------|
                    | `recommendation.name` | 제품 이름 | `"아이패드 에어 4세대"` |
                    | `recommendation.category` | 제품 카테고리 | `"태블릿"` |
                    | `recommendation.main_reason` | 주요 추천 이유 | `"가격대비 성능이 우수"` |
                    | `recommendation.sub_reason` | 부가적인 추천 이유 | `"디자인이 예쁘고 성능이 좋음"` |
                    | `recommendation.good_person` | 추천 대상 리스트 | `["영상 감상을 좋아하는 사람", "멀티태스킹을 자주 하는 사람"]` |
                    | `recommendation.bad_person` | 추천하지 않는 대상 리스트 | `["저가형 태블릿을 찾는 사람", "가격이 민감한 사람"]` |

                    ### 🔹 Specifications (제품 사양)

                    | 입력 변수명 | 설명 | 입력 예시 |
                    |------------|------|----------|
                    | `display.size` | 디스플레이 크기 | `"10.9인치"` |
                    | `display.resolution` | 해상도 | `"2360 x 1640"` |
                    | `display.refresh_rate` | 주사율 | `"60Hz"` |
                    | `display.description` | 디스플레이 설명 | `"고화질 영상 감상에 적합"` |
                    | `processor.model` | 프로세서 모델명 | `"Apple A14 Bionic"` |
                    | `processor.equivalent` | 동급 성능의 기기 | `"아이폰 12 등급"` |
                    | `processor.description` | 프로세서 설명 | `"일반적인 웹서핑 및 멀티태스킹에 충분"` |
                    | `storage.options` | 저장 옵션 | `["64GB"]` |
                    | `storage.expandable` | 확장 가능 여부 | `"128GB 옵션 없음"` |
                    | `storage.description` | 저장소 설명 | `"기본 사용에는 충분하지만 대용량 저장에는 한계"` |
                    | `battery.capacity` | 배터리 용량 | `"최대 10시간 사용 가능"` |
                    | `battery.description` | 배터리 설명 | `"일반적인 사용에는 문제없음"` |
                    | `design.features` | 디자인 특징 | `["베젤 축소", "홈 버튼 제거", "지문 인식 탑재"]` |
                    | `design.description` | 디자인 설명 | `"깔끔하고 현대적인 디자인"` |
                    | `color_options.color_options` | 색상 옵션 | `["블루", "핑크", "옐로우", "실버"]` |
                    | `pencil_support.supported` | 지원되는 펜슬 | `"애플펜슬 1세대"` |
                    | `pencil_support.charging` | 충전 방식 | `"번거로운 충전 방식 (별매)"` |
                    | `pencil_support.description` | 펜슬 관련 설명 | `"필기 및 그릴 작업에 적합"` |
                    | `charging_port.type` | 충전 포트 타입 | `"USB-C"` |
                    | `charging_port.limitation` | 충전 포트 제한 사항 | `"라이트닝 미지원"` |
                    | `charging_port.description` | 충전 포트 설명 | `"기존 아이폰 충전기 사용 불가, 데이터 전송 속도 제한"` |
                    ---
                    ## 📌 Purchase_Info_Stores 클래스

                    | 입력 변수명 | 설명 | 입력 예시 |
                    |------------|------|----------|
                    | `site` | 판매 사이트 | `"쿠팡"` |
                    | `option` | 제품 옵션 | `"블루, 64GB, Wi-Fi"` |
                    | `price` | 구매 가격 | `"508,880원"` |
                    | `purchase_link` | 구매 링크 | `"https://www.cupang.com/"` |
                    | `rating` | 판매처 평점 | `5.0` |
                        """
                        
        prompt=f""" 당신은 분석 전문가입니다 아주 조금의 데이터만으로 필요한 정보를 찾아내는 달인입니다.
                    이번에는 제품 사양서에서 추출된 데이터로 유저 요청에 알맞게 다음 양식의 테이블을 작성하려 합니다.
                    아래의 테이블을 작성해주세요.
                    {table_content}
                    <작성 규약>
                    0. 테이블에 입력할 정보를 A로 칭하고 이를 위해 제공한 정보를 B로 칭합니다. 
                    1. 첫번째 단계 유저 요청을 확인하고 A를 어떻게 구성할지 파악합니다. 또한 같이 들어온 질문이 있다면 이를 확인하고 문제해결에 도움이 될만한 답변을 찾습니다. 해당 답변은 [[answer::답변내용]]으로 반환합니다.
                    2. 두번째 단계 B를 분석하고 파악합니다. 어떤 정보를 활용가능한지 어떤정보는 불필요한지 정제하고 수집합니다.
                    3. 세번째 단계 2번의 결과를 이용하여 최대한 정밀하게 A를 구성합니다.
                    4. 3번의 결과에서 유저의 요청과 일치하지않는 부분을 확인합니다. 이에 대헤 스스로 의문점이 있는지 확인압니다.
                    4-1 정보가 부족하다고 판단되면 반드시 3회까지 스스로에게 질문을 던져서 정말로 그런지 단 한칸도 채울수 없는지 확인해서 최대한 정확한 정보를 제공합니다.질문은 다음양식으로 반환해야합니다. [[selfquestion::질문내용]]
                    4-2 스스로에게 던지는 질문임을 잊지 말고 질문을 반환합니다.
                    5. 마지막으로 자료에 포함되어 있지만 채우지 않은 정보가 있는지 다시 확인한다.
                    [최종 단계]
                    반환을 준비합니다. 반환은 두 종류중 하나를 선택 가능합니다. 
                    첫번쨰, 현재 결과가 미비하다고 느낀다면 최대 3회까지 스스로에게 질문을 던질 수 있습니다. 질문은 다음양식으로 반환해야합니다. [[selfquestion::질문내용]]
                    두번째, 현재 결과가 만족스럽다면 결과를 반환합니다. 결과는 다음 양식으로 반환해야합니다. [[display.size::디스플레이 크기]],[[display.resolution::해상도]],
                    [[display.refresh_rate::주사율]],[[display.description::디스플레이 설명]],[[processor.model::프로세서 모델명]],[[processor.equivalent::동급 성능의 기기]],
                    [[processor.description::프로세서 설명]],[[storage.options::저장 옵션]],[[storage.expandable::확장 가능 여부]],[[storage.description::저장소 설명]],
                    [[battery.capacity::배터리 용량]],[[battery.description::배터리 설명]],[[design.features::디자인 특징]],[[design.description::디자인 설명]],[[color_options.color_options::색상 옵션]],
                    [[pencil_support.supported::지원되는 펜슬]],[[pencil_support.charging::충전 방식]],[[pencil_support.description::펜슬 관련 설명]],[[charging_port.type::충전 포트 타입]],
                    [[charging_port.limitation::충전 포트 제한 사항]],[[charging_port.description::충전 포트 설명]],[[recommendation.name::제품 이름]],[[recommendation.category::제품 카테고리]],
                    [[recommendation.main_reason::주요 추천 이유]],[[recommendation.sub_reason::부가적인 추천 이유]],[[recommendation.good_person::추천 대상 리스트]],[[recommendation.bad_person::추천하지 않는 대상 리스트]]]
                    [[site::판매 사이트]],[[option::제품 옵션]],[[price::가격]],[[purchase_link::구매 링크]],[[rating::판매처 평점]]
                    최종적으로 비어있는 내용이있는지 확인합니다 만약 비어있는 내용이 있다면 스스로에게 질문을 던지고 질문은 다음양식으로 반환해야합니다. [[selfquestion::질문내용]] 내용이 완전하다면 질문은 반환하지 않습니다.질문은 매번 새로운 질문으로 변화를 줍니다.
                    최종 시도에서는 비어있는 내용이 있다 하더라도 질문은 반환하지 않고, 나머지 값은 그대로 출력합니다. 하지만 {require_key}의 내용은 반드시 더 신경써서 채워야 합니다.
                    반환은 추가 문구 없이 결과한 반환합니다.
                    """
        ##############################################
        data=input
        section1=[]
        section2=[]
        model=Node(prompt)
        selfquestion=[]
        selfanswer=[]
        context=f"""
                    
                    다음은 테이블을 채우기 위해 제공되는 정보들입니다.
                    제품 스펙 및 전문가 소견 : {data}
        """
        cachepath=".Specification_cache.h5"
        find_dict={data["제품명"].replace(" ",""):[]}
        cache_key=data["제품명"].replace(" ","")
        reject_key=None
        #####################################################################
        super().__init__(
            data=data,
            section1=section1,
            section2=section2,
            table_content=table_content,
            prompt=prompt,
            query=query,
            model=model,
            script=script,
            selfquestion=selfquestion,
            selfanswer=selfanswer,
            context=context,
            cachepath=cachepath,
            find_dict=find_dict,
            cache_key=cache_key,
            require_key=require_key,
            reject_key=reject_key
        )

async def test_sepcification_main(): 
    input=test_set
    query = "애플의 아이패드 디지털 드로잉에 적합한 제품 리뷰 영상이 필요합니다. 우수한 펜 반응속도와 고급형 프로세서를 탑재한 제품에 관한 정보가 포함된 클립이 있으면 좋겠으며 예산은 100만원입니다. 이 영상에서는 해당 제품의 기능 요약 및 인상적인 장면, 사용자 리뷰 등의 정보를 제공해주길 원합니다."
    reporter=SpecificationReporter(input,query)
    result,response=reporter.get_response()
    PurchaseKey=["site","option","price","purchase_link","rating"]
    Purchase = {}
    for key in PurchaseKey:
        if key in result[0]:
            Purchase[key] = result[0].pop(key)
    
    generator = ResultTemplate()
    result_dict = generator.dict 
    Purchase_Info = Purchase_Info_Stores()
    item_product=Product()
    try:
        Purchase_Info.process_dict(Purchase)
        Purchase_Info.set_value(result_dict)
    except Exception as e:
        print(e)
        print(f"오류가 발생했습니다.반환값:{result[0]}")        
    try:
        item_product.process_dict(result[0])
        item_product.set_value(result_dict)
    except Exception as e:
        print(e)
        print(f"오류가 발생했습니다.반환값:{result[0]}")
    import pprint
    pprint.pprint(result_dict, width=150) 
    return item_product, []
async def sepcification_main(input,query): 
    reporter=SpecificationReporter(input,query)
    result,response=reporter.get_response()
    PurchaseKey=["site","option","price","purchase_link","rating"]
    Purchase = {}
    for key in PurchaseKey:
        if key in result[0]:
            Purchase[key] = result[0].pop(key)
    Purchase_Info = Purchase_Info_Stores()
    item_product=Product()
    try:
        Purchase_Info.process_dict(Purchase)
    except Exception as e:
        print(e)
        print(f"오류가 발생했습니다.반환값:{result[0]}")        
    try:
        item_product.process_dict(result[0])
    except Exception as e:
        print(e)
        print(f"오류가 발생했습니다.반환값:{result[0]}")
    output={}
    output['Purchase']=Purchase_Info
    output['Product']=item_product
    return output, reporter

if __name__ == "__main__":
    #input=get_test_dummy()
    #reporter=SpecificationReporter(input)
    #result,response=reporter.get_response()
    #generator = ResultTemplate()
    #result_dict = generator.dict
    #item_product=Product()
#
    #try:
    #    item_product.process_dict(result[0])
    #    item_product.set_value(result_dict)
    #except Exception as e:
    #    print(e)
    #    print(f"오류가 발생했습니다.반환값:{result[0]}")
    #import pprint
    #pprint.pprint(result_dict, width=150)
    import asyncio
    item_product, result =asyncio.run(test_sepcification_main())
    #generator = ResultTemplate()
    #result_dict = generator.dict
    #item_product.set_value(result_dict)
    import pprint
    pprint.pprint(item_product, width=150)
    
    
    
