FROM alpine:3.20

RUN apk add --no-cache openssh git py3-pip py3-psycopg2

# 用 UID 1000 创建 git 用户（对齐 app 容器的 perseus 用户）
RUN mkdir -p /data/repositories && \
    adduser -D -u 1000 -h /home/git -s /usr/local/bin/git-shell-wrapper git && \
    passwd -u git && \
    ssh-keygen -A

# SSH 公钥查询脚本
COPY authorized_keys_query.py /usr/local/bin/authorized_keys_query
RUN chmod +x /usr/local/bin/authorized_keys_query

# Git Shell 包装器
COPY git-shell-wrapper /usr/local/bin/git-shell-wrapper
RUN chmod +x /usr/local/bin/git-shell-wrapper

# sshd_config
RUN sed -i \
    -e 's/^#AuthorizedKeysCommand none/AuthorizedKeysCommand \/usr\/local\/bin\/authorized_keys_query/' \
    -e 's/^#AuthorizedKeysCommandUser nobody/AuthorizedKeysCommandUser git/' \
    -e 's/^#Port 22/Port 2222/' \
    -e 's/^#PermitRootLogin.*/PermitRootLogin no/' \
    -e 's/^#PasswordAuthentication.*/PasswordAuthentication no/' \
    -e 's/^#PubkeyAuthentication.*/PubkeyAuthentication yes/' \
    /etc/ssh/sshd_config

EXPOSE 2222
CMD ["/usr/sbin/sshd", "-D", "-e"]
