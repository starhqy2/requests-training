#!-*- coding:utf-8 -*-
import requests
from bs4 import BeautifulSoup as BS
import get_page
import re
import copy
import lxml
import xlsxwriter
import cProfile
import socket
import datetime
from multiprocessing import Pool

#利用requests模拟浏览器抓取页面
def get_page(url):
    headers = {
        'User-Agent':r'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) 'r'Chrome/45.0.2454.85 Safari/537.36 155Browser/6.0.3',
        'Referer': r'http://bj.fangjia.com/ershoufang/',
        'Host': r'bj.fangjia.com',
        'Connection': 'keep-alive'
        }
    r = requests.get(url, headers = headers)
    return r

#根据关键字key在网页page中获得对应字段的字典返回
def get_search(page, key):
    soup = BS(page.text, 'lxml')
    search_list = soup.find_all(href=re.compile(key))
    search_dict = {}
    for i in search_list:
        key = i.text
        value = i['href']
        search_dict[key] = value
    return search_dict

#遍历嵌套字典，返回所有地址的嵌套列表。
def get_info_list(search_dict, layer, tmp_list, search_list):
    layer += 1 
    for key in search_dict:
        tmp_key = key
        tmp_list.append(tmp_key)
        tmp_value = search_dict[tmp_key]
        if isinstance(tmp_value, str):
            tmp_list.append(tmp_value)
            search_list.append(copy.deepcopy(tmp_list))
            tmp_list = tmp_list[:layer]
            
        elif tmp_value == '':
            layer = 1
            tmp_list = []
        else:
            get_info_list(tmp_value, layer, tmp_list, search_list)
            tmp_list = tmp_list[:layer]
    return search_list

#获取每一地址每一页面的地址列表（总页数暂时不知如何统计， 用10页代替总页数）
def get_info_pn_list(search_list):
    url_prefix = 'http://bj.fangjia.com' 
    fin_search_list = []
    for i in range(len(search_list)):
        print('>>>正在抓取%s' % search_list[i][:3])
        search_url = search_list[i][3]

        try:
            page = get_page(search_url)
        except:
            print('获取页面超时')
            continue
        soup = BS(page.text, 'lxml')
        try:
            url_suffix = soup('a', {"class": "page-num"})[0]['href']
        except:
            print('无法获得分页信息，url:%s' % search_url)
            continue
        url = url_prefix + url_suffix
        pattern = re.compile(r'e-\d+')
        for num in range(10):
            num += 1
            url_tmp = pattern.sub('e-%s' % num, url, 1)
            tmp_url_list = copy.deepcopy(search_list[i][:3])
            tmp_url_list.append(url_tmp)
            fin_search_list.append(tmp_url_list)
    return fin_search_list

#获取最终页面的每一住房信息，包括地址，价格，大小，户型等。
def get_info(fin_search_list, process_i):
    print('进程%s开始' % process_i)
    fin_info_list = []
    for i in range(len(fin_search_list)):
        url = fin_search_list[i][3]
        print('url',url)
        try:
            page = get_page(url)
        except:
            print('获取tag超时')
            continue
        soup = BS(page.text, 'lxml')
        title_list = soup.find_all('a',{'class': 'h_name'})
        address_list = soup.find_all('span', {'class': 'address'})
        attr_list = soup.find_all('span', {'class': 'attribute'})
        price_list = soup.find_all('span',{'class': 'xq_aprice xq_esf_width'})
        for num in range(20):
            tag_tmp_list = []
            
            try:
                title = title_list[num]['title']
                print(r'***********正在获取%s*********' % title)
                address = re.sub('\n', '', address_list[num].text)
                area = re.search('\d+[\u4E00-\u9FA5]{2}', attr_list[num].text).group(0)
                layout = re.search('\d[^0-9]\d.', attr_list[num].get_text()).group(0)
                floor = re.search('\d/\d', attr_list[num].get_text()).group(0)
                price = re.search('\d+[\u4E00-\u9FA5]', price_list[num].get_text()).group(0)
                unit_price = re.search('\d+[\u4E00-\u9FA5]/.', price_list[num].get_text()).group(0)
                tag_tmp_list = copy.deepcopy(fin_search_list[i][:3])
                for tag in [title, address, area, layout, floor, price, unit_price]:
                    tag_tmp_list.append(tag)
                fin_info_list.append(tag_tmp_list)
            except:
                print('【抓取失败】')
                continue
        print('进程%s结束' % process_i)
    return fin_info_list

#将地址列表分块，用于多线程计算
def assignment_search_list(fin_search_list, project_num):
    assignment_list = []
    fin_search_list_len = len(fin_search_list)
    for i in range(0, fin_search_list_len, project_num):
        start = i
        end = i + project_num
        assignment_list.append(fin_search_list[start: end])
    return assignment_list

#保存输入列表为xlsx.
def save_excel(fin_info_list, file_name):
    tag_name = ['区域', '板块', '地铁', '标题', '位置', '平米', '户型', '楼层', '总价', '单位平米价格']
    book = xlsxwriter.Workbook(r'D:\%s.xlsx' % file_name)
    tmp = book.add_worksheet()
    row_num = len(fin_info_list)
    for i in range(1, row_num):
        if i == 1:
            tag_pos = 'A%s' % i
            tmp.write_row(tag_pos, tag_name)

        else:
            con_pos = 'A%s' % i
            content = fin_info_list[i-1]
            tmp.write_row(con_pos, content)
    book.close()
                             



                
if __name__ == '__main__':
    starttime = datetime.datetime.now()
    search_list = []
    tmp_list = []
    layer = -1
    base_url = r'http://bj.fangjia.com/ershoufang/'
    
    
    file_name = input('输入保存文件名')
    fin_save_list = []
    #一级筛选
    page = get_page(base_url)
    search_dict = get_search(page, 'r-')
    #二级筛选
    for k in search_dict:
        print(r'**********************一级抓取:正在抓取【%s】********************' %k)
        url = search_dict[k]
        second_page = get_page(url)
        second_search_dict = get_search(second_page, 'b-')
        search_dict[k] = second_search_dict
    #三级筛选
    for k in search_dict:
        second_dict = search_dict[k]
        for s_k in second_dict:
            print(r'******************二级抓取：正在抓取【%s】****************' % s_k)
            url = second_dict[s_k]
            third_page = get_page(url)
            third_search_dict = get_search(third_page, 'w-')
            print('%s>%s' % (k, s_k))
            
            search_dict[k][s_k] = third_search_dict
    fin_info_list = get_info_list(search_dict, layer, tmp_list, search_list)
    fin_info_pn_list = get_info_pn_list(fin_info_list)
    #fin_save_list = get_info(fin_info_pn_list,1)
    
    p = Pool(4)
    assignment_list = assignment_search_list(fin_info_pn_list, 4)
    result = []
    for i in range(len(assignment_list)):
        result.append(p.apply_async(get_info, args=(assignment_list[i], i)))
    p.close()
    p.join()
    for result_i in range(len(result)):
        fin_info_result_list = result[result_i].get()
        fin_save_list.extend(fin_info_result_list)
        
    save_excel(fin_save_list, file_name)
    endtime = datetime.datetime.now()
    time = (endtime-starttime).seconds
    print('总共用时： %s s' % time)
    

    
    
    
                  
