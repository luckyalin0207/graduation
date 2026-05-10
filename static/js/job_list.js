/**
 * job_list.js — 职位列表页面逻辑
 * URLs 和 CSRF token 从 #_urls data 属性读取，避免模板引号冲突
 */

// ── Toast 提示函数 ────────────────────────────────────────
function showToast(message, type) {
  var bgColor = type === 'success' ? '#1cc88a' : 
                type === 'error' ? '#e74a3b' : '#36b9cc';
  var icon = type === 'success' ? 'fa-check-circle' :
             type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle';
  
  var toast = $('<div>')
    .css({
      position: 'fixed',
      top: '20px',
      right: '20px',
      background: bgColor,
      color: 'white',
      padding: '12px 20px',
      borderRadius: '8px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      zIndex: 9999,
      fontSize: '14px',
      fontWeight: '500',
      minWidth: '200px'
    })
    .html('<i class="fas ' + icon + ' mr-2"></i>' + message)
    .appendTo('body');
  
  setTimeout(function() {
    toast.fadeOut(300, function() {
      $(this).remove();
    });
  }, 3000);
}

$(function () {
  // ── 读取 Django 注入的 URL 和 CSRF ──────────────────────
  var $u = $('#_urls');
  var URL_LIST    = $u.data('list');
  var URL_COMPARE = $u.data('compare');
  var URL_FAV     = $u.data('fav');
  var URL_SEND    = $u.data('send');
  var CSRF        = $u.attr('data-csrf');

  var currentPage = 1;
  var pageSize    = 10;
  var selectedIds = [];
  var verifiedCache = {};   // { companyName: 'ok'|'bad'|'risk' }
  var pendingSendId = null;

  // ── 筛选状态对象 ──────────────────────────────────────────
  var filters = {
    keyword:      '',
    city:         '',
    experience:   '',
    edu:          '',
    company_type: '',
    scale:        '',
    source:       '',
    price_min:    '',
    price_max:    '',
    only_favorite: ''
  };

  // ── 预加载已验证公司状态 ──────────────────────────────────
  $.get('/company/api/list/', { limit: 500 }, function (res) {
    if (res.code === 0) {
      res.data.forEach(function (o) {
        if (o.status === 'verified') {
          verifiedCache[o.company_name] =
            o.risk_level === '高' ? 'risk' : o.is_normal ? 'ok' : 'bad';
        }
      });
    }
  });

  // ── Tag 按钮点击：单选切换 ────────────────────────────────
  $(document).on('click', '.filter-tag', function () {
    var field = $(this).data('field');
    var val   = $(this).data('val');
    // 同组取消其他激活
    $('[data-field="' + field + '"]').removeClass('active btn-secondary').addClass('btn-outline-secondary');
    $(this).removeClass('btn-outline-secondary').addClass('active btn-secondary');
    filters[field] = val;
    // 城市自定义输入清空
    if (field === 'city') $('#cityCustom').val('');
    updateFilterBadges();
    loadJobs(1);
  });

  // ── 城市自定义输入 ────────────────────────────────────────
  $('#cityCustom').on('keypress', function (e) {
    if (e.which === 13) {
      var v = $(this).val().trim();
      if (v) {
        $('[data-field="city"]').removeClass('active btn-secondary').addClass('btn-outline-secondary');
        filters.city = v;
        updateFilterBadges();
        loadJobs(1);
      }
    }
  });

  // ── 薪资快选 ──────────────────────────────────────────────
  $(document).on('click', '.sal-preset', function () {
    $('.sal-preset').removeClass('btn-secondary').addClass('btn-outline-secondary');
    $(this).removeClass('btn-outline-secondary').addClass('btn-secondary');
    filters.price_min = $(this).data('min');
    filters.price_max = $(this).data('max');
    $('#salMin').val(filters.price_min);
    $('#salMax').val(filters.price_max);
    updateFilterBadges();
    loadJobs(1);
  });

  // ── 薪资手动输入 ──────────────────────────────────────────
  $('#salMin, #salMax').on('change', function () {
    filters.price_min = $('#salMin').val();
    filters.price_max = $('#salMax').val();
    $('.sal-preset').removeClass('btn-secondary').addClass('btn-outline-secondary');
    updateFilterBadges();
    loadJobs(1);
  });

  // ── 只看收藏 ──────────────────────────────────────────────
  $('#onlyFav').on('change', function () {
    filters.only_favorite = $(this).is(':checked') ? '1' : '';
    loadJobs(1);
  });

  // ── 搜索按钮 ──────────────────────────────────────────────
  $('#searchBtn').click(function () {
    filters.keyword = $('#kwInput').val().trim();
    loadJobs(1);
  });
  $('#kwInput').on('keypress', function (e) {
    if (e.which === 13) {
      filters.keyword = $(this).val().trim();
      loadJobs(1);
    }
  });

  // ── 重置按钮 ──────────────────────────────────────────────
  $('#resetBtn').click(function () {
    filters = { keyword:'', city:'', experience:'', edu:'', company_type:'', scale:'', source:'', price_min:'', price_max:'', only_favorite:'' };
    $('#kwInput').val('');
    $('#salMin, #salMax').val('');
    $('#cityCustom').val('');
    $('#onlyFav').prop('checked', false);
    $('.filter-tag').removeClass('active btn-secondary').addClass('btn-outline-secondary');
    $('.filter-tag[data-val=""]').removeClass('btn-outline-secondary').addClass('active btn-secondary');
    $('.sal-preset').removeClass('btn-secondary').addClass('btn-outline-secondary');
    updateFilterBadges();
    loadJobs(1);
  });

  // ── 筛选标签展示 ──────────────────────────────────────────
  var filterLabels = {
    keyword: '关键词', city: '城市', experience: '经验', edu: '学历',
    company_type: '公司类型', scale: '规模', source: '来源',
    price_min: '最低薪资', price_max: '最高薪资'
  };

  function updateFilterBadges() {
    var badges = '';
    var hasFilter = false;
    Object.keys(filterLabels).forEach(function (k) {
      var v = filters[k];
      if (v && v !== '') {
        hasFilter = true;
        badges += '<span class="badge badge-primary mr-1" style="font-size:12px;cursor:pointer" data-clear="' + k + '">'
          + filterLabels[k] + ': ' + v + ' &times;</span>';
      }
    });
    if (hasFilter) {
      $('#activeFilters').removeClass('d-none');
      $('#filterBadges').html(badges);
    } else {
      $('#activeFilters').addClass('d-none');
    }
  }

  // 点击筛选标签清除单个筛选
  $(document).on('click', '[data-clear]', function () {
    var k = $(this).data('clear');
    filters[k] = '';
    if (k === 'price_min') { $('#salMin').val(''); }
    if (k === 'price_max') { $('#salMax').val(''); }
    if (['city','experience','edu','company_type','scale','source'].indexOf(k) !== -1) {
      $('[data-field="' + k + '"][data-val=""]').removeClass('btn-outline-secondary').addClass('active btn-secondary');
      $('[data-field="' + k + '"]:not([data-val=""])').removeClass('active btn-secondary').addClass('btn-outline-secondary');
    }
    updateFilterBadges();
    loadJobs(1);
  });

  // ── 对比选择 ──────────────────────────────────────────────
  function updateCompareBtn() {
    $('#compareCount').text(selectedIds.length);
    $('#compareBtn').prop('disabled', selectedIds.length < 2);
  }

  $(document).on('change', '.job-check', function () {
    var id = $(this).val();
    if ($(this).is(':checked')) {
      if (selectedIds.length >= 4) {
        $(this).prop('checked', false);
        alert('最多同时对比4个职位');
        return;
      }
      selectedIds.push(id);
    } else {
      selectedIds = selectedIds.filter(function (i) { return i !== id; });
    }
    updateCompareBtn();
  });

  $('#checkAll').change(function () {
    var chk = $(this).is(':checked');
    $('.job-check').each(function () {
      if (chk && selectedIds.length < 4) {
        $(this).prop('checked', true);
        var id = $(this).val();
        if (!selectedIds.includes(id)) selectedIds.push(id);
      } else {
        $(this).prop('checked', false);
        selectedIds = selectedIds.filter(function (i) { return i !== $(this).val(); }.bind(this));
      }
    });
    updateCompareBtn();
  });

  // ── 加载职位列表 ──────────────────────────────────────────
  function loadJobs(page) {
    currentPage = page || 1;
    var params = {
      page: currentPage, limit: pageSize,
      keyword:      filters.keyword,
      edu:          filters.edu,
      city:         filters.city || $('#cityCustom').val().trim(),
      price_min:    filters.price_min,
      price_max:    filters.price_max,
      company_type: filters.company_type,
      scale:        filters.scale,
      experience:   filters.experience,
      only_favorite: filters.only_favorite,
      source:       filters.source
    };
    $.ajax({
      url: URL_LIST, type: 'GET', data: params,
      success: function (res) {
        if (res.code === 0) {
          renderTable(res.data);
          renderPagination(res.count);
        }
      }
    });
  }

  // ── 渲染表格 ──────────────────────────────────────────────
  function renderTable(data) {
    var html = '';
    if (data && data.length > 0) {
      data.forEach(function (item) {
        var chk = selectedIds.includes(String(item.job_id)) ? 'checked' : '';

        // 来源徽章
        var sb = '';
        if (item.source === 'BOSS直聘')
          sb = '<span class="badge badge-warning" style="font-size:10px">BOSS</span>';
        else if (item.source === '51job')
          sb = '<span class="badge badge-primary" style="font-size:10px">51job</span>';
        else if (item.source)
          sb = '<span class="badge badge-secondary" style="font-size:10px">' + item.source + '</span>';

        // 企业验证状态图标
        var vs = verifiedCache[item.company] || '';
        var vi = vs === 'ok'   ? '<i class="fas fa-check-circle v-ok" title="已验证：经营正常"></i>'
               : vs === 'bad'  ? '<i class="fas fa-exclamation-circle v-bad" title="已验证：经营异常"></i>'
               : vs === 'risk' ? '<i class="fas fa-exclamation-triangle v-risk" title="高风险企业"></i>'
               : '';

        // 公司名（可点击验证）
        var cn = (item.company || '-').substring(0, 15);
        var coBtn = '<button class="co-btn btn-verify-company" data-company="'
          + encodeURIComponent(item.company || '') + '">' + cn + ' ' + vi + '</button>';

        // 操作按钮
        var sendBtn = item.is_sent
          ? '<button class="btn btn-secondary btn-sm mr-1" disabled>已投递</button>'
          : '<button class="btn btn-primary btn-sm mr-1 btn-send" data-id="' + item.job_id
            + '" data-href="' + encodeURIComponent(item.href || '') + '">投递</button>';

        var favBtn = item.is_favorited
          ? '<button class="btn btn-warning btn-sm btn-fav" data-id="' + item.job_id + '" data-action="cancel">已收藏</button>'
          : '<button class="btn btn-outline-warning btn-sm btn-fav" data-id="' + item.job_id + '" data-action="favorite">收藏</button>';

        html += '<tr>'
          + '<td><input type="checkbox" class="job-check" value="' + item.job_id + '" ' + chk + '></td>'
          + '<td>' + item.job_id + '</td>'
          + '<td>' + (item.name || '').substring(0, 20) + '</td>'
          + '<td>' + (item.salary || '-') + '</td>'
          + '<td>' + (item.place || '-').substring(0, 10) + '</td>'
          + '<td>' + (item.education || '-') + '</td>'
          + '<td>' + (item.experience || '-').substring(0, 8) + '</td>'
          + '<td>' + coBtn + '</td>'
          + '<td>' + sb + '</td>'
          + '<td>' + (item.key_word || '-') + '</td>'
          + '<td>' + sendBtn + ' ' + favBtn + '</td>'
          + '</tr>';
      });
    } else {
      html = '<tr><td colspan="11" class="text-center text-muted py-4">暂无数据</td></tr>';
    }
    $('#jobTableBody').html(html);
  }

  // ── 分页 ──────────────────────────────────────────────────
  function renderPagination(total) {
    var tp = Math.ceil(total / pageSize);
    var html = '';
    html += '<li class="page-item ' + (currentPage <= 1 ? 'disabled' : '') + '">'
      + '<a class="page-link" href="javascript:;" data-page="' + (currentPage - 1) + '">上一页</a></li>';
    var s = Math.max(1, currentPage - 2);
    var e = Math.min(tp, currentPage + 2);
    for (var i = s; i <= e; i++) {
      html += '<li class="page-item ' + (i === currentPage ? 'active' : '') + '">'
        + '<a class="page-link" href="javascript:;" data-page="' + i + '">' + i + '</a></li>';
    }
    html += '<li class="page-item ' + (currentPage >= tp ? 'disabled' : '') + '">'
      + '<a class="page-link" href="javascript:;" data-page="' + (currentPage + 1) + '">下一页</a></li>';
    html += '<li class="page-item disabled"><span class="page-link">共 ' + total + ' 条</span></li>';
    $('#pagination').html(html);
  }

  // ── 搜索 & 分页事件 ───────────────────────────────────────
  $('#searchBtn').click(function () { loadJobs(1); });
  $('input[name=keyword]').on('keypress', function (e) {
    if (e.which === 13) loadJobs(1);
  });
  $('#pagination').on('click', 'a.page-link', function () {
    var pg = $(this).data('page');
    if (pg && !$(this).parent().hasClass('disabled')) loadJobs(pg);
  });

  // ── 职位对比 ──────────────────────────────────────────────
  $('#compareBtn').click(function () {
    if (selectedIds.length < 2) return;
    $.get(URL_COMPARE, { ids: selectedIds.join(',') }, function (res) {
      if (res.code !== 0) return;
      var jobs = res.data;
      var fields = [
        ['职位名称', 'name'], ['公司', 'company'], ['薪资', 'salary'],
        ['城市', 'city'], ['学历', 'education'], ['经验', 'experience'],
        ['公司类型', 'company_type'], ['规模', 'scale'], ['行业', 'industry']
      ];
      var h = '<div class="table-responsive"><table class="table table-sm"><thead><tr><th>对比项</th>';
      jobs.forEach(function (j) { h += '<th>' + j.name.substring(0, 16) + '</th>'; });
      h += '</tr></thead><tbody>';
      fields.forEach(function (f) {
        h += '<tr><td class="text-muted">' + f[0] + '</td>';
        jobs.forEach(function (j) { h += '<td>' + (j[f[1]] || '-') + '</td>'; });
        h += '</tr>';
      });
      h += '</tbody></table></div>';
      $('#compareBody').html(h);
      $('#compareModal').modal({ backdrop: false, keyboard: true });
    });
  });

  // ── 收藏 ──────────────────────────────────────────────────
  $('#jobTableBody').on('click', '.btn-fav', function () {
    var jobId  = $(this).data('id');
    var action = $(this).data('action');
    var btn    = $(this);
    $.ajax({
      url: URL_FAV, type: 'POST',
      data: { job_id: jobId, action: action, csrfmiddlewaretoken: CSRF },
      success: function (res) {
        if (res.code === 0) {
          if (action === 'favorite') {
            btn.text('已收藏').removeClass('btn-outline-warning').addClass('btn-warning').data('action', 'cancel');
          } else {
            btn.text('收藏').removeClass('btn-warning').addClass('btn-outline-warning').data('action', 'favorite');
          }
        } else { alert(res.msg); }
      }
    });
  });

  // ── 投递：智能处理有无链接的情况 ────────────────────────────
  $('#jobTableBody').on('click', '.btn-send', function () {
    var jobId = $(this).data('id');
    var href  = decodeURIComponent($(this).data('href') || '');
    var btn   = $(this);
    pendingSendId = jobId;
    
    if (href && href !== 'undefined' && href !== 'null') {
      // 情况1: 有原始链接 - 直接打开 + 自动记录
      window.open(href, '_blank');
      
      btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> 记录中...');
      
      $.ajax({
        url: URL_SEND,
        type: 'POST',
        data: { 
          job_id: jobId, 
          action: 'send', 
          csrfmiddlewaretoken: CSRF 
        },
        success: function (res) {
          if (res.code === 0) {
            btn.text('已投递')
               .removeClass('btn-primary')
               .addClass('btn-secondary')
               .prop('disabled', true)
               .removeClass('btn-send');
            showToast('✓ 投递成功，已记录到系统', 'success');
          } else {
            btn.text('投递')
               .removeClass('btn-secondary')
               .addClass('btn-primary')
               .prop('disabled', false);
            showToast('记录失败: ' + res.msg, 'error');
          }
        },
        error: function (xhr) {
          btn.text('投递')
             .removeClass('btn-secondary')
             .addClass('btn-primary')
             .prop('disabled', false);
          showToast('网络错误，请稍后重试', 'error');
        }
      });
    } else {
      // 情况2: 无原始链接 - 显示搜索链接弹窗
      $('#sendModalBody').html(
        '<div class="text-center py-4"><div class="spinner-border text-primary"></div>'
        + '<p class="mt-2 text-muted">正在加载职位信息...</p></div>'
      );
      $('#sendOrigLink').addClass('d-none');
      $('#confirmSendBtn').prop('disabled', false).html('<i class="fas fa-bookmark mr-1"></i>记录投递进度');
      $('#sendModal').modal({ backdrop: false, keyboard: true });

      $.when(
        $.get('/job/api/detail/' + jobId + '/'),
        $.get('/api/resume-summary/')
      ).done(function (jr, rr) {
        var job    = (jr[0] || {}).data || {};
        var resume = (rr[0] || {}).data || {};
        renderSendModal(job, resume);
      }).fail(function () {
        $('#sendModalBody').html('<div class="alert alert-danger">加载失败，请重试</div>');
      });
    }
  });

  function buildSearchLinks(job) {
    var name    = encodeURIComponent(job.name    || '');
    var company = encodeURIComponent(job.company || '');
    var links   = '';

    // 根据来源构建对应平台的搜索链接
    var src = (job.source || '').toLowerCase();
    if (src.indexOf('boss') !== -1 || src.indexOf('直聘') !== -1) {
      links += '<a href="https://www.zhipin.com/web/geek/job?query=' + name + '&city=100010000" target="_blank" class="btn btn-sm btn-warning mr-2">'
        + '<i class="fas fa-search mr-1"></i>在 BOSS直聘 搜索</a>';
    } else if (src.indexOf('51job') !== -1 || src.indexOf('前程') !== -1) {
      links += '<a href="https://we.51job.com/pc/search?keyword=' + name + '&searchType=2" target="_blank" class="btn btn-sm btn-primary mr-2">'
        + '<i class="fas fa-search mr-1"></i>在 51job 搜索</a>';
    }

    // 通用：在各平台搜索该公司的职位
    if (job.company) {
      links += '<a href="https://www.zhipin.com/web/geek/job?query=' + company + '&city=100010000" target="_blank" class="btn btn-sm btn-outline-secondary mr-2">'
        + '<i class="fas fa-building mr-1"></i>搜索该公司职位</a>';
    }

    // 如果没有任何链接，给一个通用搜索
    if (!links) {
      links = '<a href="https://www.zhipin.com/web/geek/job?query=' + name + '&city=100010000" target="_blank" class="btn btn-sm btn-outline-secondary mr-2">'
        + '<i class="fas fa-search mr-1"></i>在招聘平台搜索</a>';
    }

    return links;
  }

  function renderSendModal(job, resume) {
    var h = '';

    // ── 功能说明提示 ──────────────────────────────────────────
    h += '<div class="alert alert-info py-2 mb-3 small">'
      + '<i class="fas fa-info-circle mr-2"></i>'
      + '<strong>该职位暂无直接投递链接。</strong>请点击下方按钮在招聘平台搜索该职位，完成投递后点击"记录投递进度"。'
      + '</div>';

    // ── 职位信息 ──────────────────────────────────────────────
    h += '<div class="border rounded p-3 mb-3">';
    h += '<h6 class="font-weight-bold mb-1">' + (job.name || '') + '</h6>';
    h += '<div class="d-flex flex-wrap text-muted small" style="gap:12px">';
    h += '<span><i class="fas fa-building mr-1"></i>' + (job.company || '-') + '</span>';
    h += '<span><i class="fas fa-map-marker-alt mr-1"></i>' + (job.place || '-') + '</span>';
    h += '<span><i class="fas fa-coins mr-1"></i>' + (job.salary || '薪资面议') + '</span>';
    h += '<span><i class="fas fa-graduation-cap mr-1"></i>' + (job.education || '不限') + '</span>';
    h += '<span><i class="fas fa-clock mr-1"></i>' + (job.experience || '不限') + '</span>';
    h += '</div>';

    // ── 搜索链接 ───────────────────────────────────────────────
    var searchLinks = buildSearchLinks(job);
    h += '<div class="mt-3">' + searchLinks + '</div>';
    h += '</div>';

    // ── 简历信息 ──────────────────────────────────────────────
    h += '<h6 class="font-weight-bold mb-2"><i class="fas fa-file-alt mr-2 text-primary"></i>将以此简历投递</h6>';
    if (!resume.has_resume) {
      h += '<div class="alert alert-warning py-2">'
        + '<i class="fas fa-exclamation-triangle mr-2"></i>您尚未上传简历！'
        + '<a href="/users/user_info/" class="alert-link" target="_blank">立即上传</a>，提高投递成功率。</div>';
    } else {
      h += '<div class="d-flex align-items-center p-2 bg-light rounded mb-2">'
        + '<i class="fas fa-file-pdf fa-2x text-danger mr-3"></i>'
        + '<div>'
        + '<div class="font-weight-bold">' + (resume.resume_name || '简历文件') + '</div>'
        + '<small class="text-muted">'
        + resume.user_name
        + (resume.degree ? ' · ' + resume.degree : '')
        + (resume.school ? ' · ' + resume.school : '')
        + '</small>'
        + '</div></div>';
      if (resume.skills) {
        h += '<p class="small mb-1 text-muted"><i class="fas fa-code mr-1"></i><strong>技能：</strong>' + resume.skills + '</p>';
      }
      h += '<p class="small mb-0 text-muted"><i class="fas fa-briefcase mr-1"></i><strong>工作经历：</strong>' + resume.work_count + ' 段</p>';
    }

    // ── 企业验证状态 ──────────────────────────────────────────
    var vs = verifiedCache[job.company] || '';
    h += '<div class="mt-2">';
    if (vs === 'ok') {
      h += '<div class="alert alert-success py-2 mb-0 small">'
        + '<i class="fas fa-check-circle mr-2"></i>企业已验证：经营状态正常</div>';
    } else if (vs === 'bad' || vs === 'risk') {
      h += '<div class="alert alert-warning py-2 mb-0 small">'
        + '<i class="fas fa-exclamation-triangle mr-2"></i>注意：该企业存在风险记录，请谨慎投递</div>';
    } else {
      h += '<div class="alert alert-light py-2 mb-0 small border">'
        + '<i class="fas fa-shield-alt mr-2 text-muted"></i>企业信息未验证，'
        + '<a href="#" class="verify-in-modal" data-company="'
        + encodeURIComponent(job.company || '') + '">点击验证企业</a></div>';
    }
    h += '</div>';

    $('#sendModalBody').html(h);
  }

  // 确认投递
  $('#confirmSendBtn').click(function () {
    if (!pendingSendId) return;
    var btn = $(this);
    btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin mr-1"></i>记录中...');
    $.ajax({
      url: URL_SEND, type: 'POST',
      data: { job_id: pendingSendId, action: 'send', csrfmiddlewaretoken: CSRF },
      success: function (res) {
        if (res.code === 0) {
          $('#sendModal').modal('hide');
          $('.btn-send[data-id="' + pendingSendId + '"]')
            .text('已投递').removeClass('btn-primary').addClass('btn-secondary')
            .prop('disabled', true).removeClass('btn-send');
          showToast('✓ 投递成功，已记录到系统', 'success');
          pendingSendId = null;
        } else {
          btn.prop('disabled', false).html('<i class="fas fa-bookmark mr-1"></i>记录投递进度');
          showToast('记录失败: ' + res.msg, 'error');
        }
      },
      error: function (xhr) {
        btn.prop('disabled', false).html('<i class="fas fa-bookmark mr-1"></i>记录投递进度');
        showToast('投递失败，请重试', 'error');
      }
    });
  });

  // 投递弹窗内点击验证
  $('#sendModalBody').on('click', '.verify-in-modal', function (e) {
    e.preventDefault();
    var co = decodeURIComponent($(this).data('company'));
    $('#sendModal').modal('hide');
    setTimeout(function () { openCompanyModal(co); }, 400);
  });

  // ── 企业验证弹窗 ──────────────────────────────────────────
  function openCompanyModal(name) {
    if (!name) return;
    $('#modalCoName').text(name);
    $('#coDetailLink').addClass('d-none');
    $('#companyModalBody').html(
      '<div class="text-center py-4"><div class="spinner-border text-primary"></div>'
      + '<p class="mt-2 text-muted">正在查询企业信息...</p></div>'
    );
    $('#companyModal').modal({ backdrop: false, keyboard: true });

    $.ajax({
      url: '/company/api/verify/', method: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({ company_name: name }),
      headers: { 'X-CSRFToken': CSRF },
      success: function (resp) {
        renderCompanyModal(resp, name);
        var d2   = resp.data || {};
        var info = d2.data || {};
        if (d2.status === 'verified') {
          verifiedCache[name] = info.risk_level === '高' ? 'risk'
            : info.is_normal ? 'ok' : 'bad';
          loadJobs(currentPage);
        }
      },
      error: function () {
        $('#companyModalBody').html('<div class="alert alert-danger">网络请求失败，请稍后重试</div>');
      }
    });
  }

  $('#jobTableBody').on('click', '.btn-verify-company', function () {
    openCompanyModal(decodeURIComponent($(this).data('company')));
  });

  function renderCompanyModal(resp, name) {
    var d2     = resp.data || {};
    var info   = d2.data || {};
    var status = d2.status;

    if (status === 'verified' && info.company_name) {
      var isOk      = info.is_normal;
      var riskColors = { '低': 'success', '中': 'warning', '高': 'danger', '未知': 'secondary' };
      var rColor    = riskColors[info.risk_level] || 'secondary';
      var statusCls = isOk ? 'success' : 'danger';
      var statusTxt = info.business_status || (isOk ? '正常' : '异常');

      var h = '<div class="d-flex align-items-center justify-content-between mb-3"><div>';
      h += '<span class="badge badge-pill badge-' + statusCls + ' px-3 py-2 mr-2">' + statusTxt + '</span>';
      h += '<span class="badge badge-pill badge-' + rColor + ' px-3 py-2">'
        + (info.risk_level || '未知') + '风险</span></div>';
      h += (d2.cached
        ? '<small class="text-muted"><i class="fas fa-clock mr-1"></i>缓存于 ' + (d2.verified_at || '') + '</small>'
        : '<small class="text-success"><i class="fas fa-sync-alt mr-1"></i>实时数据</small>') + '</div>';

      h += '<div class="row">';
      var flds = [
        ['统一信用代码', info.unified_code],
        ['法定代表人',   info.legal_person],
        ['注册资本',     info.registered_capital],
        ['成立日期',     info.establishment_date],
        ['企业类型',     info.company_type],
        ['所属行业',     info.industry],
        ['人员规模',     info.staff_size],
        ['联系电话',     info.phone],
        ['在招职位数',   info.job_count ? info.job_count + ' 个' : ''],
        ['薪资范围',     info.salary_range],
        ['在招城市',     info.cities],
      ];
      flds.forEach(function (f) {
        if (f[1]) {
          h += '<div class="col-sm-6 mb-2">'
            + '<small class="text-muted">' + f[0] + '</small>'
            + '<div class="font-weight-bold small">' + f[1] + '</div></div>';
        }
      });
      h += '</div>';

      if (info.registered_address) {
        h += '<div class="mb-2"><small class="text-muted">注册地址</small>'
          + '<p class="mb-0 small">' + info.registered_address + '</p></div>';
      }

      var rs = info.risk_summary || '暂无风险记录';
      h += rs !== '暂无风险记录'
        ? '<div class="alert alert-warning py-2 mb-0"><i class="fas fa-exclamation-triangle mr-2"></i>' + rs + '</div>'
        : '<div class="alert alert-success py-2 mb-0"><i class="fas fa-check-circle mr-2"></i>暂无风险记录</div>';

      // 数据来源说明
      if (info.data_source_note) {
        h += '<div class="mt-2 text-right"><small class="text-muted">' + info.data_source_note + '</small></div>';
      }

      $('#companyModalBody').html(h);
      $('#coDetailLink')
        .attr('href', 'https://aiqicha.baidu.com/s?q=' + encodeURIComponent(name))
        .removeClass('d-none');

    } else if (status === 'not_found') {
      $('#companyModalBody').html(
        '<div class="text-center py-4">'
        + '<i class="fas fa-search fa-3x text-warning mb-3 d-block"></i>'
        + '<h6>未找到该企业信息</h6>'
        + '<p class="text-muted small">请确认公司名称是否为完整工商注册名称</p></div>'
      );
      $('#coDetailLink')
        .attr('href', 'https://aiqicha.baidu.com/s?q=' + encodeURIComponent(name))
        .removeClass('d-none');
    } else {
      $('#companyModalBody').html(
        '<div class="alert alert-warning"><i class="fas fa-exclamation-circle mr-2"></i>'
        + (resp.msg || '查询失败，请稍后重试') + '</div>'
      );
    }
  }

  // ── 工具函数 ──────────────────────────────────────────────
  function getCsrf() {
    var v = null;
    document.cookie.split(';').forEach(function (c) {
      var p = c.trim().split('=');
      if (p[0] === 'csrftoken') v = decodeURIComponent(p[1]);
    });
    return v;
  }

  // ── 初始加载 ──────────────────────────────────────────────
  loadJobs(1);
});
