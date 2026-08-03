package git

func (g *Git) Clone(url, dest string, cred Credential) error {
	args := append(gitCredArgs(url, cred), "clone", url, dest)
	_, err := g.run("", args...)
	return err
}

func (g *Git) Push(dir, remote, branch string, cred Credential) error {
	var ref string
	if branch == "HEAD" {
		ref = "HEAD"
	} else {
		ref = branch
	}
	args := append(gitCredArgs(remoteURL(g, dir, remote), cred), "push", remote, ref)
	_, err := g.run(dir, args...)
	return err
}

func (g *Git) Pull(dir, remote, branch string, cred Credential) error {
	args := append(gitCredArgs(remoteURL(g, dir, remote), cred), "pull", remote, branch)
	_, err := g.run(dir, args...)
	return err
}

func remoteURL(g *Git, dir, remote string) string {
	out, err := g.run(dir, "config", "--get", "remote."+remote+".url")
	if err != nil {
		return ""
	}
	return trimSpace(out)
}

func gitCredArgs(url string, cred Credential) []string {
	switch cred.Type {
	case "token":
		if url != "" {
			return []string{"-c", "http.extraHeader=Authorization: Bearer " + cred.Token}
		}
	case "ssh":
		if cred.SSHKeyPath != "" {
			return []string{"-c", "core.sshCommand=ssh -i " + cred.SSHKeyPath + " -o IdentitiesOnly=yes -o BatchMode=yes"}
		}
	}
	return nil
}
