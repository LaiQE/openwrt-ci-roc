'use strict';
'require view';
'require form';
'require fs';
'require ui';

return view.extend({
	load: function() {
		return L.resolveDefault(fs.exec('/usr/bin/srun-autologin', [ 'status' ]), {
			code: 1,
			stdout: 'state=unknown\nupdated=-\nmessage=无法读取运行状态\nbinary=unknown\n',
			stderr: ''
		});
	},

	runAction: function(action) {
		return fs.exec('/usr/bin/srun-autologin', [ action ]).then(function(result) {
			var text = result.stdout || result.stderr || _('命令已执行，请查看系统日志。');
			ui.addNotification(null, E('pre', { 'style': 'white-space:pre-wrap' }, [ text ]), 'info');
		}).catch(function(err) {
			ui.addNotification(null, E('p', {}, [ err.message ]), 'error');
		});
	},

	render: function(status) {
		var m, s, o;
		var statusText = status.stdout || status.stderr || _('尚无状态');

		m = new form.Map('srun-autologin', _('校园网自动认证'),
			_('定期检查外网连通性；断网时调用 srun 完成深澜认证。密码会以明文保存在路由器 UCI 配置中，请妥善保护。'));

		s = m.section(form.NamedSection, 'main', 'srun', _('基本设置'));
		s.anonymous = true;
		s.addremove = false;

		o = s.option(form.Flag, 'enabled', _('启用服务'));
		o.default = '0';
		o.rmempty = false;

		o = s.option(form.Value, 'username', _('账号'));
		o.rmempty = false;

		o = s.option(form.Value, 'password', _('密码'));
		o.password = true;
		o.rmempty = false;
		o.description = _('密码以明文写入 /etc/config/srun-autologin，仅 root 可读。');

		o = s.option(form.Value, 'server', _('认证服务器'));
		o.default = 'http://net.zju.edu.cn';
		o.rmempty = false;
		o.validate = function(sectionId, value) {
			return /^https?:\/\/[^\s/]+(?::\d+)?(?:\/.*)?$/.test(value) || _('请输入以 http:// 或 https:// 开头的 URL。');
		};

		o = s.option(form.Value, 'if_name', _('认证网卡'));
		o.placeholder = 'wan / eth0.2';
		o.description = _('可留空让 srun 从认证服务器响应中自动探测 IP。与固定 IP 同时填写时优先使用固定 IP。');

		o = s.option(form.Value, 'ip', _('固定认证 IP'));
		o.datatype = 'ip4addr';
		o.placeholder = _('可选');

		o = s.option(form.Value, 'check_host', _('连通性测试地址'));
		o.default = '223.5.5.5';
		o.rmempty = false;
		o.description = _('应选择一个校外、稳定且允许 ICMP 的地址。任何一次 ping 成功即认为网络正常。');

		o = s.option(form.ListValue, 'check_count', _('最多 ping 次数'));
		o.value('1', '1');
		o.value('2', '2');
		o.value('3', '3');
		o.default = '3';
		o.rmempty = false;

		o = s.option(form.Value, 'check_timeout', _('每次超时（秒）'));
		o.datatype = 'and(uinteger,min(1),max(10))';
		o.default = '2';
		o.rmempty = false;

		o = s.option(form.Value, 'interval', _('检查间隔（秒）'));
		o.datatype = 'and(uinteger,min(15))';
		o.default = '600';
		o.rmempty = false;

		s = m.section(form.NamedSection, 'main', 'srun', _('srun 高级参数'));
		s.anonymous = true;
		s.addremove = false;

		o = s.option(form.Flag, 'strict_bind', _('严格绑定'));
		o.default = '0';
		o.rmempty = false;

		o = s.option(form.Flag, 'double_stack', _('双栈'));
		o.default = '0';
		o.rmempty = false;

		o = s.option(form.Value, 'retry_delay', _('重试延迟（毫秒）'));
		o.datatype = 'uinteger';
		o.default = '1000';
		o.rmempty = false;

		o = s.option(form.Value, 'retry_times', _('认证重试次数'));
		o.datatype = 'and(uinteger,min(1))';
		o.default = '3';
		o.rmempty = false;

		o = s.option(form.Value, 'n', _('参数 n'));
		o.datatype = 'integer';
		o.default = '200';
		o.rmempty = false;

		o = s.option(form.Value, 'type', _('认证类型'));
		o.datatype = 'integer';
		o.default = '1';
		o.rmempty = false;

		o = s.option(form.Value, 'acid', _('AC ID'));
		o.datatype = 'integer';
		o.default = '60';
		o.rmempty = false;

		o = s.option(form.Value, 'os', _('操作系统'));
		o.default = 'Windows';
		o.rmempty = false;

		o = s.option(form.Value, 'name', _('设备名称'));
		o.default = 'Windows 10';
		o.rmempty = false;

		o = s.option(form.Flag, 'download_enabled', _('缺失时自动下载 srun'));
		o.default = '1';
		o.rmempty = false;
		o.description = _('离线安装包已内置 srun；该选项用于文件意外丢失后的恢复。未认证时 GitHub 可能不可达。');

		o = s.option(form.Value, 'release_url', _('下载地址前缀'));
		o.default = 'https://github.com/zu1k/srun/releases/download/0.6.2';
		o.rmempty = false;

		s = m.section(form.TypedSection, '_runtime', _('运行状态'));
		s.anonymous = true;
		s.addremove = false;
		s.cfgsections = function() { return [ '_status' ]; };

		o = s.option(form.DummyValue, '_status', _('最近状态'));
		o.cfgvalue = function() { return statusText; };

		o = s.option(form.Button, '_check', _('立即检查'));
		o.inputtitle = _('检查并按需认证');
		o.inputstyle = 'apply';
		o.onclick = L.bind(this.runAction, this, 'run');

		o = s.option(form.Button, '_login', _('立即认证'));
		o.inputtitle = _('强制调用 srun');
		o.inputstyle = 'action';
		o.onclick = L.bind(this.runAction, this, 'login');

		o = s.option(form.Button, '_download', _('重新下载二进制'));
		o.inputtitle = _('下载 srun 0.6.2');
		o.inputstyle = 'action';
		o.onclick = L.bind(this.runAction, this, 'download');

		return m.render();
	}
});
