strVal = 'data science'  # 문자열 변수
nVal = 12345  # 정수형 변수
fVal = 1.2  # 실수형 변수
lVal = ['data', 'science']  # 리스트
dVal = {'lecture': 'data science'}  # 딕셔너리
bVal = True  # 논리형 변수(참/거짓)

# 기본적인 주석
strVal
nVal
fVal
lVal
dVal
bVal
print('strVal : ', strVal)
print('nVal : ', nVal)
print('fVal : ', fVal)
print('lVal : ', lVal)
print('dVal : ', dVal)
print('bVal : ', bVal)
print('strVal : ', type(strVal))
print('nVal : ', type(nVal))
print('fVal : ', type(fVal))
print('lVal : ', type(lVal))
print('dVal : ', type(dVal))
print('bVal : ', type(bVal))
'''
같은 변수명일 경우, 이전 데이터를 덮어씀
'''
nVal = 16  # 정수형 변수
fVal = 3.14  # 실수형 변수
print('10진수 표현 : ', nVal)  # 10진수
print('2진수 표현 : ', bin(nVal))  # 2진수
print('8진수 표현 : ', oct(nVal))  # 8진수
print('16진수 표현 : ', hex(nVal))  # 16진수
btVal = True  # 논리형 변수(참)
bfVal = False  # 논리형 변수(거짓)

btVal = TRUE  # 논리형 변수(참) - 오류
bfVal = FALSE  # 논리형 변수(거짓) - 오류
btVal = true  # 논리형 변수(참) - 오류
bfVal = false  # 논리형 변수(거짓) - 오류

10 == 11
10 != 11
10 >= 11
10 <= 11
10 > 11
10 < 11
nBig = 100
nSmall = 10
print(nBig == nSmall)
print(nBig != nSmall)
print(nBig >= nSmall)
print(nBig <= nSmall)
print(nBig > nSmall)
print(nBig < nSmall)

print(nBig= < nSmall)  # 오류
print(nBig= > nSmall)  # 오류
strData = 'data'  # 문자열 변수
strSci = "Science"  # 문자열 변수
strLecture = strData + strSci
strLecture
strLecture = strData + " " + strSci
strLecture
strLecture.split()  # split()으로 공백을 기준으로 문자열 구분
lSeperate = strLecture.split()  # split()으로 공백을 기준으로 문자열 구분아혀 lSeperate 변수에 저장
type(lSeperate)
strHello = "안녕하세요. 반갑습니다."
strHello.find("반갑")  # 문자열을 찾기 위해 find() 함수를 이용
# 문자열을 있으면, 첫번째 시작 인덱스를 반환
strHello.find("hello")  # 문자열이 없으면, -1을 리턴
"반갑" in strHello  # in 명령어를 사용하여 확인 가능 : if 조건문에서 활용
strHello.replace('.', '?')  # .을 모두 ?로 변경
strHello.replace('.', '?')
strHello.replace("하세요", "하셔유")  # 안녕하셔유? 가 될까요?
strHello  # 원본 데이터는 변하지 않음
strNewHello = strHello.replace('.', '?')  # strHello를 replace하여 strNewHello에 저장
strNewHello = strNewHello.replace("하세요", "하셔유")  # strNewHello를 replace하여 strNewHello에 저장
strNewHello
strHello.strip('반갑습니다.')  # strip()함수를 이용하여 "반갑습니다."를 제거
strHello  # 역시 원본 데이터는 변하지 않음
lnData = [1, 2, 3, 4, 5]  # lnData를 리스트로 생성
print(lnData)
print('type : ', type(lnData))
print(lnData[0])  # lnData 리스트의 0번 인덱스의 값 출력
print(lnData[3])  # lnData 리스트의 3번 인덱스의 값 출력
lnData[0] = lnData[4]  # lnData[4]의 값을 lnData[0]에 저장
print(lnData)  # lnData 리스트를 출력
print(lnData[2:4])  # lnData[4]에 저장된 5는 출력되지 않음
lnData = [1, 2, 3, 4, 5]
lstrData = ['a', 'b', 'c']

# 두 개의 서로다른 자료형을 가진 리스트를 병합
lnData + lstrData
lnData.append(10)  # 10을 맨 뒤에 추가
lnData
lnData.insert(0, 'python')  # 'python'문자열을 0번 인덱스에 추가하고, 기존 인덱스에 저장된 데이터는 하나씩 뒤로 밀림(인덱스가 +1 추가)
lnData
lnData.remove('python')  # 'python' 데이터를 삭제
lnData
del lnData[5]  # del 명령어를 통해 인덱스를 지정하여 삭제
lnData
lnData
lnData.pop(0)  # 0번 인덱스의 데이터를 삭제
lnData
lnData.pop()  # 인덱스 지정이 없으면, 마지막 인덱스의 값을 삭제
lnData
lnData.clear()  # 리스트의 모든 데이터를 삭제
lnData
# 튜플의 기본 구조
tVal = ("사과", "딸기", "바나나", "토마토", "키위")

print(tVal)
print(type(tVal))
# 튜플에 저장된 데이터는 변경이 불가능
tVal[0] = "포도"
# count() 함수를 이용하여 튜플에 저장된 특정 데이터의 개수를 확인
tData = (1, 2, 3, 1, 2, 3, 4, 5, 1, 2, 7)
tData.count(1)
# len()함수를 이용하여 튜플에 저장된 전체 데이터 개수를 확인
len(tVal)

len(tData)

print(tData[2:5])
tTuple = tVal + tData
print(tTuple)
tData * 2
tData
tData2 = tData * 2
print(tData2)
print("tVal memory = ", hex(id(tVal)))
tVal = tVal * 2
print("tVal memory = ", hex(id(tVal)))
print(tVal)
print("tVal memory = ", hex(id(tVal)))
tVal = tVal + tVal
print("tVal memory = ", hex(id(tVal)))
print(tVal)
sVal = {1, 2, 3, 4, 5}
print(sVal)
print(type(sVal))

sVal[1:2]
# add 함수를 이용하여 데이터를 추가할 수 있음
sVal.add(100)
print(sVal)
# update 함수를 이용하여 여러개의 데이터를 추가할 수 있음
sVal.update([200, 300])
print(sVal)
# remove 함수를 이용하여 데이터를 삭제할 수 있음
sVal.remove(200)
print(sVal)
# clear() 함수를 이용하여 데이터를 초기화 할 수 있음
sVal.clear()
print(sVal)
sVal = {100, 200, 300, 400, 500}
sData = {"a", "b", "c", "c", 100, 300}
print(sVal)
print(sData)
# intersection() 함수를 이용하여 교집합을 만들 수 있음
sVal.intersection(sData)
# deference() 함수를 이용하여 차집합을 만들 수 있음
sVal.difference(sData)
# "-" 연산자로도 가능
sVal - sData
# union() 함수를 이용하여 합집합을 만들 수 있음
sVal.union(sData)
# "+"연산자는 불가능
sVal + sData
# symetric_difference()를 이용하여 합집합에서 교집합을 뺀 집합을 만들 ㅅ ㅜ있음
sVal.symmetric_difference(sData)

# 딕셔너리 기본 구조는 다음과 같이 표현할 수 있음
dVal = {
    'name': '이컴공',
    'email': 'computer@hoseo.edu',
    'address': '충남 아산시'
}
print(dVal)
print(type(dVal))

dData = {
    "사과": 300,
    "포도": 200,
    "배": 500,
    "키위": 100
}

# 키를 이용한 항목 검색
print(dData["배"])

# get() 함수를 이용한 항목 검색
dData.get("배")

# 새로운 키 추가를 통한 항목 추가
dData["딸기"] = 100
print(dData)

# pop을 이용한 항목 삭제
dData.pop("사과")

dData

dData.pop()

# sorted 함수를 이용한 정렬
sorted(dData)

# sorted와 values 함수를 이용하여 값을 정렬할 수 있음
sorted(dData.values())

# 실제 dData는 변화가 없음
dData


# 함수 f(x)를 생성하고 x 값을 입력으로 받음
def f(x):
    # x에 10을 더한 값을 출력
    return x + 10

    f(2)